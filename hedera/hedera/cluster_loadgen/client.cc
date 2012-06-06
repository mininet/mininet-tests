//****************************************************************************/
// File:            client.cc
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
#define BUFSIZE_UDP 9450
#define MAX_LINE_LEN 256

#define TYPE_TCP 1
#define TYPE_RPC 2
#define TYPE_UDP 3

struct traffic_gen_info
{
    // these fields only set once
    struct sockaddr_in dstaddr;
    int dest_random;
    double start_time;
    double stop_time;
    int type;
    long long flow_size;
    int flow_size_random;
    long long repetitions;
    double time_between_flows;
    int time_between_flows_random;
    double rpc_delay;
    int rpc_delay_random;
    // these fields change
    int sock;
    long long bytes_transferred;
    double time_elapsed; // FIXME: This looks unused. Can be removed
    long long bytes_left;
    long long repetitions_left;
    double next_start_time;
    unsigned int seed;
    int rpc_request_sent;
    int done;
};

vector<struct traffic_gen_info *>tgen_info_vector;
struct in_addr my_addr;
char send_buf[BUFSIZE];
char recv_buf[BUFSIZE];

struct in_addr get_interface_addr(const char *interface);
int parse_input_file(char *filename, vector<struct traffic_gen_info *> &tgen_info_vector, int *line_count, int *field_count);
void start_flow(struct traffic_gen_info *tgen_info);
void send_fake_rpc_request(struct traffic_gen_info *tgen_info);
void send_recv_data(struct traffic_gen_info *tgen_info);
in_addr_t get_random_ip(struct traffic_gen_info *tgen_info);

void *client_thread_main(void *arg)
{
    vector<struct traffic_gen_info *>::iterator iter;
    struct traffic_gen_info *tgen_info;
    int done;
    //double curr_test_time;

    memset(send_buf, 0, BUFSIZE);
    done = 0;
    while(!done && !interrupted)
    {
	done = 1; // assume done for now, will check later
	for (iter = tgen_info_vector.begin(); iter != tgen_info_vector.end(); iter++)
	{
	    tgen_info = *iter;
	    //curr_test_time = get_test_time();

	    if (!tgen_info->done)
	    {
		if (curr_test_time >= tgen_info->stop_time)
		{
		    if (verbosity > 1)
			printf("generator reached stop time\n");
		    tgen_info->done = 1;
		    if (close(tgen_info->sock) == -1)
			perror("close");
		}
		else
		{
		    done = 0; // at least one generator is not done
		    if (curr_test_time >= tgen_info->next_start_time)
		    {
			if (tgen_info->bytes_left == 0)
			    start_flow(tgen_info); // note: this will modify bytes_left
			if (tgen_info->type == TYPE_RPC && !tgen_info->rpc_request_sent)
			    send_fake_rpc_request(tgen_info);
			if (tgen_info->bytes_left > 0)
			    send_recv_data(tgen_info);
		    }
		}
	    }
	}
    }
    for (iter = tgen_info_vector.begin(); iter != tgen_info_vector.end(); iter++)
    {
	tgen_info = *iter;
	free(tgen_info);
    }
    if (verbosity > 0)
	printf("client thread terminated\n");

    return NULL;
}

void client_init()
{
    int line_count;
    int field_count;
    // get my ip address, for filtering input file
    my_addr = get_interface_addr(net_interface);

    if (parse_input_file(input_filename, tgen_info_vector, &line_count, &field_count))
    {
	printf("error parsing input file, line_count = %d, field_count = %d\n", line_count, field_count);
	exit(1);
    }
    else if (verbosity > 0)
    {
	printf("processed %d lines\n", (int)tgen_info_vector.size());
    }
}

struct in_addr get_interface_addr(const char *interface)
{
    int sock;
    struct ifreq ifr;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
    {
	perror("socket");
	exit(1);
    }
    ifr.ifr_addr.sa_family = AF_INET;
    strncpy(ifr.ifr_name, interface, IFNAMSIZ-1);
    if (ioctl(sock, SIOCGIFADDR, &ifr) == -1)
    {
	perror("ioctl");
	exit(1);
    }
    if (close(sock) == -1)
	perror("close");

    return ((struct sockaddr_in *)&ifr.ifr_addr)->sin_addr;
}

int parse_input_file(char *filename, vector<struct traffic_gen_info *> &tgen_info_vector, int *line_count, int *field_count)
{
    FILE *infile;
    char line[MAX_LINE_LEN];
    char *token;
    char *saveptr;
    struct traffic_gen_info *tgen_info;
    struct in_addr tmp_addr;
    unsigned int tmp_uint;
    long long tmp_long_long;
    unsigned short tmp_ushort;
    double tmp_double;

    (*line_count) = 0;

    infile = fopen(filename, "r");
    if (infile == NULL)
    {
	perror("fopen");
	return -1;
    }

    if(verbosity > 2) {
	printf("Parsing input file: %s\n", filename);
    }

    while (fgets(line, MAX_LINE_LEN, infile) != NULL)
    {
	if(verbosity > 2) {
	    printf("%s", line);
	}
	(*line_count)++;
	(*field_count) = 0;

	// comments
	if (line[0] == '#')
	    continue;

	// source host (is it me?)
	(*field_count)++;
	token = strtok_r(line, " \t\n", &saveptr);
	if (token == NULL || !inet_aton(token, &tmp_addr))
	    return -1;
	if (tmp_addr.s_addr != my_addr.s_addr) {
	    if(verbosity > 2) {
		char str[INET_ADDRSTRLEN];
		inet_ntop(AF_INET, &(my_addr), str, INET_ADDRSTRLEN);
		printf("token: '%s', my_addr: '%s'\n", token, str);
		printf("token: '%d', my_addr: '%d'\n", tmp_addr.s_addr, my_addr.s_addr);
	    }
	    continue;
	}

	if(verbosity > 2) {
	    printf("It's me!\n");
	}

	// ok, allocate the structure
	tgen_info = (struct traffic_gen_info *)malloc(sizeof(struct traffic_gen_info));
	if (tgen_info == NULL)
	{
	    perror("malloc");
	    return -1;
	}

	// desination host
	memset(&tgen_info->dstaddr, 0, sizeof(struct sockaddr_in));
	tgen_info->dstaddr.sin_family = AF_INET;
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (!strcmp(token, "random"))
	    tgen_info->dest_random = 1;
	else
	{
	    if (token == NULL || !inet_aton(token, &tmp_addr))
		return -1;
	    tgen_info->dstaddr.sin_addr = tmp_addr;
	}

	// destination port
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_ushort(token, &tmp_ushort))
	    return -1;
	tgen_info->dstaddr.sin_port = htons(tmp_ushort);

	// flow type
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL)
	    return -1;
	else if (!strcmp(token, "TCP"))
	    tgen_info->type = TYPE_TCP;
	else if (!strcmp(token, "RPC"))
	    tgen_info->type = TYPE_RPC;
	else if (!strcmp(token, "UDP"))
	    tgen_info->type = TYPE_UDP;
	else
	    return -1;

	// seed
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_uint(token, &tmp_uint))
	    return -1;
	tgen_info->seed = tmp_uint;

	// start time
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_double(token, &tmp_double))
	    return -1;
	tgen_info->start_time = tmp_double;

	// stop time
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_double(token, &tmp_double))
	    return -1;
	tgen_info->stop_time = tmp_double;

	// flow size
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_long_long(token, &tmp_long_long))
	    return -1;
	tgen_info->flow_size = tmp_long_long;

	// flow size random?
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL)
	    return -1;
	else if (!strcmp(token, "random"))
	    tgen_info->flow_size_random = 1;
	else if (!strcmp(token, "exact"))
	    tgen_info->flow_size_random = 0;
	else
	    return -1;

	// number of repetitions
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_long_long(token, &tmp_long_long))
	    return -1;
	tgen_info->repetitions = tmp_long_long;

	// time between flows
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL || !read_double(token, &tmp_double))
	    return -1;
	tgen_info->time_between_flows = tmp_double;

	// time between flows random?
	(*field_count)++;
	token = strtok_r(NULL, " \t\n", &saveptr);
	if (token == NULL)
	    return -1;
	else if (!strcmp(token, "random"))
	    tgen_info->time_between_flows_random = 1;
	else if (!strcmp(token, "exact"))
	    tgen_info->time_between_flows_random = 0;
	else
	    return -1;

	// RPC delay, RPC delay random: only apply to RPC
	if (tgen_info->type == TYPE_RPC)
	{
	    (*field_count)++;
	    token = strtok_r(NULL, " \t\n", &saveptr);
	    if (token == NULL || !read_double(token, &tmp_double))
		return -1;
	    tgen_info->rpc_delay = tmp_double;

	    (*field_count)++;
	    token = strtok_r(NULL, " \t\n", &saveptr);
	    if (token == NULL)
		return -1;
	    else if (!strcmp(token, "random"))
		tgen_info->rpc_delay_random = 1;
	    else if (!strcmp(token, "exact"))
		tgen_info->rpc_delay_random = 0;
	    else
		return -1;
	}

	tgen_info->bytes_left = 0;
	tgen_info->repetitions_left = tgen_info->repetitions;
	tgen_info->next_start_time = tgen_info->start_time;

	tgen_info_vector.push_back(tgen_info);
    }

    return 0;
}

double randomize(unsigned int *seed, double avg_val)
{
    return -log(1.0 - (rand_r(seed)/(double)RAND_MAX))*avg_val;
}

void start_flow(struct traffic_gen_info *tgen_info)
{
    if (tgen_info->type == TYPE_UDP)
	tgen_info->sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    else
	tgen_info->sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (tgen_info->sock < 0) {
	perror("socket");
	exit(1);
    }

    if (fcntl(tgen_info->sock, F_SETFL, O_NONBLOCK) < 0) {
	perror("fcntl");
	exit(1);
    }

    if (tgen_info->dest_random)
	tgen_info->dstaddr.sin_addr.s_addr = get_random_ip(tgen_info);

    if (tgen_info->type != TYPE_UDP)
    { 
	if (connect(tgen_info->sock, (struct sockaddr *) &tgen_info->dstaddr, sizeof(struct sockaddr)) < 0) {
	    if (errno != EINPROGRESS) {
		//printf("%s:%d errno=%d\n", __FILE__, __LINE__, errno);
		perror("connect");
		//exit(1);
		tgen_info->next_start_time = get_test_time() + 0.001;
		return;
	    }
	}
    }

    tgen_info->bytes_transferred = 0;
    /* store the size of this new flow */
    if (tgen_info->flow_size_random)
	tgen_info->bytes_left = (long long)randomize(&tgen_info->seed, tgen_info->flow_size);
    else
	tgen_info->bytes_left = tgen_info->flow_size;

    if (verbosity > 2)
    {
	if (tgen_info->type == TYPE_TCP)
	    printf("starting TCP flow of size %lld\n", tgen_info->bytes_left);
	else if (tgen_info->type == TYPE_RPC)
	    printf("starting RPC flow of size %lld\n", tgen_info->bytes_left);
	else if (tgen_info->type == TYPE_UDP)
	    printf("starting UDP flow of size %lld\n", tgen_info->bytes_left);
    }
    tgen_info->rpc_request_sent = 0;
}

void send_fake_rpc_request(struct traffic_gen_info *tgen_info)
{
    struct rpc_req_info rpc_info;
    int ret;

    rpc_info.response_length = tgen_info->bytes_left;
    if (tgen_info->rpc_delay_random)
	rpc_info.rpc_delay = randomize(&tgen_info->seed, tgen_info->rpc_delay);
    else
	rpc_info.rpc_delay = tgen_info->rpc_delay;

    ret = write(tgen_info->sock, &rpc_info, sizeof(struct rpc_req_info));
    if (ret == sizeof(struct rpc_req_info))
    {
	tgen_info->rpc_request_sent = 1;
	add_to_total_bytes_out(ret);
    }
    else if (ret == -1 && errno == EAGAIN)
    {
	// we'll try it again next time
    }
    else if (ret == -1)
    {
	//printf("%s:%d errno=%d\n", __FILE__, __LINE__, errno);
	perror("write");
	exit(1);
    }
    else
    {
	printf("only partially sent?\n");
	exit(1);
    }
}

void send_recv_data(struct traffic_gen_info *tgen_info)
{
    int send_recv_size;
    int ret;
    socklen_t socklen = sizeof (struct sockaddr_in);

    send_recv_size = BUFSIZE;
    if (tgen_info->bytes_left < BUFSIZE)
	send_recv_size = tgen_info->bytes_left;
    /*
     * Avoid fragmentation in case of UDP
     */
    if ((tgen_info->type == TYPE_UDP) && (send_recv_size > BUFSIZE_UDP))
    {
	send_recv_size = BUFSIZE_UDP;
    }

    if (tgen_info->type == TYPE_TCP)
    {
	ret = write(tgen_info->sock, send_buf, send_recv_size);
	if (ret > 0)
	{
	    tgen_info->bytes_left -= ret;
	    tgen_info->bytes_transferred += ret;
	    add_to_total_bytes_out(ret);
	}
	else if (ret == -1 && errno != EAGAIN)
	{
	    //printf("%s:%d errno=%d\n", __FILE__, __LINE__, errno);
	    perror("write");
	    //exit(1);
	}
    }
    else if (tgen_info->type == TYPE_RPC)
    {
	ret = read(tgen_info->sock, recv_buf, send_recv_size);
	if (ret > 0)
	{
	    tgen_info->bytes_left -= ret;
	    tgen_info->bytes_transferred += ret;
	    add_to_total_bytes_in(ret);
	}
	else if (ret == -1 && errno != EAGAIN)
	{
	    perror("read");
	    exit(1);
	}
    }
    else if (tgen_info->type == TYPE_UDP)
    {
	ret = sendto(tgen_info->sock, send_buf, send_recv_size, MSG_DONTWAIT, (const struct sockaddr *)&tgen_info->dstaddr, socklen);
	if (ret > 0)
	{
	    tgen_info->bytes_left -= ret;
	    tgen_info->bytes_transferred += ret;
	    add_to_total_bytes_out(ret);
	}
	else if (ret == -1 && errno != EAGAIN)
	{
	    perror("sendto");
	    exit(1);
	}
    }

    if (tgen_info->bytes_left <= 0)
    {
	if (close(tgen_info->sock) == -1)
	    perror("close");
	tgen_info->repetitions_left--;
	if (tgen_info->repetitions_left == 0)
	{
	    if (verbosity > 1)
		printf("generator finished all flows\n");
	    tgen_info->done = 1;
	}
	else
	{
	    if (tgen_info->time_between_flows_random)
		tgen_info->next_start_time = get_test_time() + randomize(&tgen_info->seed, tgen_info->time_between_flows);
	    else
		tgen_info->next_start_time = get_test_time() + tgen_info->time_between_flows;
	}
    }
}

// FIXME: This should just go. These IP addresses cannot remain here.
//WARNING, THIS IS SPECIFIC TO THE TESTBED (LAST MINUTE BAD DESIGN)
in_addr_t get_random_ip(struct traffic_gen_info *tgen_info)
{
    int index;
    in_addr_t tmp_addr;

    const char *eth0_ips[] = {
	"192.168.1.2",
	"192.168.1.3",
	"192.168.1.4",
	"192.168.1.5",
	"192.168.1.6",
	"192.168.1.7",
	"192.168.1.8",
	"192.168.1.9",
	"192.168.1.10",
	"192.168.1.11",
	"192.168.1.12",
	"192.168.1.13",
	"192.168.1.14",
	"192.168.1.15",
	"192.168.1.16",
	"192.168.1.17"
    };
    const char *eth1_ips[] = {
	"10.0.0.2",
	"10.0.0.3",
	"10.0.1.2",
	"10.0.1.3",
	"10.1.0.2",
	"10.1.0.3",
	"10.1.1.2",
	"10.1.1.3",
	"10.2.0.2",
	"10.2.0.3",
	"10.2.1.2",
	"10.2.1.3",
	"10.3.0.2",
	"10.3.0.3",
	"10.3.1.2",
	"10.3.1.3"
    };

    do {
	index = rand_r(&tgen_info->seed) % 16;
	if (!strcmp(net_interface, "eth0"))
	    tmp_addr = inet_addr(eth0_ips[index]);
	else
	    tmp_addr = inet_addr(eth1_ips[index]);
    } while (tmp_addr == my_addr.s_addr);

    return tmp_addr;
}

