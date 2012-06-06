//****************************************************************************/
// File:            server.cc
// Authors:         Sivasankar Radhakrishnan <sivasankar@cs.ucsd.edu>
// Creation Date:   2010-06-29
//
// Copyright (C) 2010   Sivasankar Radhakrishnan
// All rights reserved.
//
// This program is free software; you can redistribute it and/or modify it
// under the terms of the GNU General Public License as published by the Free
// Software Foundation; either version 2 of the License, or (at your option)
// any later version.
//
// This program is distributed in the hope that it will be useful, but WITHOUT
// ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
// FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
// more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
//****************************************************************************/

#include "common.h"

#define BUFSIZE 65536
#define BACKLOG 100

struct client_info
{
	int sock;
	long long bytes_transferred;
	long long bytes_to_send;
	double response_time;
};

queue<struct client_info> client_info_queue;
fd_set server_readfds;
fd_set server_writefds;
int server_fdmax;
int tcp_listen_sock;
int udp_server_sock;

void server_init();
int  udp_init();
int  tcp_init();
void server_wait_on_sockets();
void accept_incoming_connections();
void recv_send_tcp();
void recv_all_udp();
void close_client_connections();

void *server_thread_main(void *arg)
{
	server_init();

  while(!interrupted)
	{
		server_wait_on_sockets();
		accept_incoming_connections();
		recv_send_tcp();
		recv_all_udp();
	}

	close_client_connections();
	close(tcp_listen_sock);
	close(udp_server_sock);

  return NULL;
}

void server_init()
{

	udp_server_sock = udp_init();
	tcp_listen_sock = tcp_init();

  FD_ZERO(&server_readfds);
  FD_ZERO(&server_writefds);
  FD_SET(tcp_listen_sock, &server_readfds);
  FD_SET(udp_server_sock, &server_readfds);
	if (tcp_listen_sock > udp_server_sock)
		server_fdmax = tcp_listen_sock;
	else
		server_fdmax = udp_server_sock;

	if (verbosity > 0)
		printf("listening on port %d\n", listen_port);
}

int udp_init()
{
  struct sockaddr_in server_addr;
  int optval;
	int sock;

  if ((sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) < 0)
	{
    perror("socket");
    exit(1);
  }

  if (fcntl(sock, F_SETFL, O_NONBLOCK) < 0)
	{
    perror("fcntl");
    exit(1);
  }
  
  optval = 1;
  if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(int)) < 0)
	{
    perror("setsockopt");
    exit(1);
  }

  memset(&server_addr, 0, sizeof(struct sockaddr_in));
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(listen_port);
  server_addr.sin_addr.s_addr = INADDR_ANY;
  if (bind(sock, (struct sockaddr *) &server_addr, sizeof(struct sockaddr_in)) < 0)
	{
    perror("bind");
    exit(1);
  }

	return sock;
}

int tcp_init()
{
  struct sockaddr_in server_addr;
  int optval;
	int sock;

  if ((sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0)
	{
    perror("socket");
    exit(1);
  }

  if (fcntl(sock, F_SETFL, O_NONBLOCK) < 0)
	{
    perror("fcntl");
    exit(1);
  }
  
  optval = 1;
  if (setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(int)) < 0)
	{
    perror("setsockopt");
    exit(1);
  }

  memset(&server_addr, 0, sizeof(struct sockaddr_in));
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(listen_port);
  server_addr.sin_addr.s_addr = INADDR_ANY;
  if (bind(sock, (struct sockaddr *) &server_addr, sizeof(struct sockaddr_in)) < 0)
	{
    perror("bind");
    exit(1);
  }

  if (listen(sock, BACKLOG) < 0)
	{
    perror("listen");
    exit(1);
  }

	return sock;
}

void server_wait_on_sockets()
{
	fd_set server_readfds_tmp;
	fd_set server_writefds_tmp;
	struct timeval timeout;

	server_readfds_tmp = server_readfds;
	server_writefds_tmp = server_writefds;
	timeout.tv_sec = 0;
	timeout.tv_usec = 100000; // check for interrupt at least every 100ms

	if (select(server_fdmax+1, &server_readfds_tmp, &server_writefds_tmp, NULL, &timeout) < 0)
	{
		if (errno != EINTR)
		{
			perror("select");
			exit(1);
		}
	}
}

void accept_incoming_connections()
{
	struct sockaddr_in client_addr;
	socklen_t addrlen;
	struct client_info client_data;
	static int first_time = 1;

	addrlen = sizeof(struct sockaddr_in);
	client_data.bytes_transferred = 0;
	client_data.bytes_to_send = 0;
	client_data.response_time = 0.0;

	client_data.sock = accept(tcp_listen_sock, (struct sockaddr *)&client_addr, &addrlen);
	while (client_data.sock >= 0)
	{
		if (first_time)
		{
			send_start_signal(); // use empty connection to signal start of experiment
			first_time = 0;
		}
		FD_SET(client_data.sock, &server_readfds); // note: will update server_fdmax later
		client_info_queue.push(client_data);
		client_data.sock = accept(tcp_listen_sock, (struct sockaddr *)&client_addr, &addrlen);
	}
	if (errno != EAGAIN)
	{
		perror("accept");
		exit(1);
	}
}

void recv_send_tcp()
{
	int retval;
	int writelen;
	static char buf[BUFSIZE];
	int num_elements;
	int i;
	struct client_info client_data;
	int close_it;

	if (tcp_listen_sock > udp_server_sock)
		server_fdmax = tcp_listen_sock;
	else
		server_fdmax = udp_server_sock;
	num_elements = client_info_queue.size();
	for (i = 0; i < num_elements; i++)
	{
		close_it = 0;
		client_data = client_info_queue.front();
		client_info_queue.pop();
		retval = recv(client_data.sock, buf, BUFSIZE, MSG_DONTWAIT);
		if (retval < 0 && errno != EAGAIN)
		{
			perror("recv");
			close_it = 1;
		}
		else if (retval < 0 && errno == EAGAIN)
		{
			// try again next time
		}
		else if (retval == 0)
		{
			close_it = 1;
		}
		else
		{
			if (retval == sizeof(struct rpc_req_info) && client_data.bytes_transferred == 0)
			{
				struct rpc_req_info *rpc_info;
				rpc_info = (struct rpc_req_info *)buf;
				if (rpc_info->response_length != 0)
				{
					client_data.bytes_to_send = rpc_info->response_length;
					client_data.response_time = rpc_info->rpc_delay + get_test_time();
					if (verbosity > 2)
					    printf("received RPC request: %lld %f\n", client_data.bytes_to_send, client_data.response_time);
					FD_SET(client_data.sock, &server_writefds);
				}
			}
			client_data.bytes_transferred += retval;
			add_to_total_bytes_in(retval);
		}
		if (!close_it && client_data.bytes_to_send > 0 && client_data.response_time <= get_test_time())
		{
			writelen = BUFSIZE;
			if (writelen > client_data.bytes_to_send)
				writelen = client_data.bytes_to_send;
			retval = send(client_data.sock, buf, writelen, MSG_DONTWAIT);
			if (retval < 0 && errno != EAGAIN)
			{
				perror("send");
				//printf("send() returned %d, errno = %d\n", retval, errno);
				close_it = 1;
			}
			else if (retval < 0 && errno == EAGAIN)
			{
				// try again next time
			}
			else if (retval == 0)
			{
				if (verbosity > 2)
					printf("send() returned 0?\n");
				close_it = 1;
			}
			else
			{
			    if (verbosity > 2)
				    printf("sent %d bytes to client, tried to send %d\n", retval, writelen);
				client_data.bytes_to_send -= retval;
				if (verbosity > 2)
					printf("bytes left to send: %lld\n", client_data.bytes_to_send);
				client_data.bytes_transferred += retval;
				add_to_total_bytes_out(retval);
			}
		}
		if (close_it)
		{
			FD_CLR(client_data.sock, &server_readfds);
			FD_CLR(client_data.sock, &server_writefds);
			close(client_data.sock);
			if (verbosity > 2)
				printf("closing client socket\n");
		}
		else
		{
			if (client_data.sock > server_fdmax)
				server_fdmax = client_data.sock;
			client_info_queue.push(client_data);
		}
	}
}

void close_client_connections()
{
	struct client_info client_data;
	int num_elements;
	int i;

	num_elements = client_info_queue.size();
	for (i = 0; i < num_elements; i++)
	{
		client_data = client_info_queue.front();
		client_info_queue.pop();
		close(client_data.sock);
	}
}

void recv_all_udp()
{
	int retval;
	static char buf[BUFSIZE];
	struct sockaddr client_addr;
    socklen_t addr_len;
    long long byte_count;

    byte_count = 0;
    retval = 0;
    do {
		retval = recvfrom(udp_server_sock, buf, BUFSIZE, MSG_DONTWAIT, &client_addr, &addr_len);
        if (retval > 0)
            byte_count += retval;
	} while (retval > 0);
	if (retval < 0 && errno != EAGAIN)
	{
		perror("recvfrom");
		exit(1);
	}
	add_to_total_bytes_in(byte_count);
	if (verbosity > 3 && byte_count > 0)
		printf("received %lld UDP bytes\n", byte_count);
}

