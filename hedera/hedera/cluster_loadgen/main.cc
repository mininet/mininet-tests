//****************************************************************************/
// File:            main.cc
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

/* exported variables */
unsigned short listen_port;
unsigned int seed_init;
int verbosity;
char *input_filename;
const char *net_interface;
volatile bool interrupted;
double curr_test_time;

/* file-scope globals */
char *prog_name;
double test_start_time;
unsigned int sample_period_us;
pthread_t server_thread;
pthread_t client_thread;
pthread_cond_t start_signal = PTHREAD_COND_INITIALIZER;
pthread_mutex_t start_signal_mutex = PTHREAD_MUTEX_INITIALIZER;
volatile long long total_bytes_in;
pthread_mutex_t total_bytes_in_mutex = PTHREAD_MUTEX_INITIALIZER;
volatile long long total_bytes_out;
pthread_mutex_t total_bytes_out_mutex = PTHREAD_MUTEX_INITIALIZER;

void usage();
void wait_for_start_signal();
void counting_thread_main();
void handleint(int signum);

int main(int argc, char *argv[])
{
	char c;

	// defaults
	input_filename = NULL;
	net_interface = "eth0";
	listen_port = 12345;
	sample_period_us = 1000000;
	//seed_init = 12345;
	verbosity = 0;

	// process args
	prog_name = argv[0];
	opterr = 0;
	while ((c = getopt(argc, argv, "f:hi:l:p:s:v")) != -1)
	{
		switch(c)
		{
			case 'f':
				input_filename = optarg;
				break;
			case 'h':
				usage();
				return 0;
			case 'i':
				net_interface = optarg;
				break;
			case 'l':
				if (!read_ushort(optarg, &listen_port))
				{
					printf("listen port invalid\n");
					return 1;
				}
				break;
			case 'p':
				if (!read_uint(optarg, &sample_period_us))
				{
					printf("sample period invalid\n");
					return 1;
				}
				break;
#if 0
			case 's':
				if (!read_uint(optarg, &seed_init))
				{
					printf("seed invalid\n");
					return 1;
				}
				break;
#endif
			case 'v':
				verbosity++;
				break;
			case '?':
				printf("unknown option: %c\n", optopt);
				usage();
				return 1;
		}
	}

	// this argument is required
  if (input_filename == NULL)
	{
		usage();
    return 1;
  }

	total_bytes_in = 0; // no other threads yet
	total_bytes_out = 0;

	interrupted = 0;
  signal(SIGINT, handleint);
  signal(SIGTERM, handleint);
  signal(SIGHUP, handleint);
  signal(SIGPIPE, handleint);
  signal(SIGKILL, handleint);

	client_init();

  pthread_create(&server_thread, NULL, server_thread_main, (void *)0);
	wait_for_start_signal();
	if (!interrupted)
	{
		start_test_timer();
		sleep(1); // wait for one second: see also start_test_timer()
		pthread_create(&client_thread, NULL, client_thread_main, (void *)0);
		counting_thread_main();
		pthread_join(client_thread, NULL);
	}
	pthread_join(server_thread, NULL);
 
  return 0;
}

void usage()
{
	printf("usage: %s options\n", prog_name);
	printf("options include:\n");
	printf("-f <filename>\n");
	printf("-h\n");
	printf("-i <interface>\n");
	printf("-l <listen_port>\n");
	printf("-p <sample_period>\n");
	printf("-s <rand_seed>\n");
	printf("-v\n");
}

void counting_thread_main()
{
	long long curr_bytes_in;
	long long prev_bytes_in;
	long long diff_bytes_in;
	long long curr_bytes_out;
	long long prev_bytes_out;
	long long diff_bytes_out;
	double curr_time;
	double prev_time;
	double diff_time;
	double rate_in;
	double rate_out;

	curr_time = get_test_time();
	curr_bytes_in = get_total_bytes_in();
	curr_bytes_out = get_total_bytes_out();
	usleep(sample_period_us);

	while(!interrupted)
	{
		prev_time = curr_time;
		prev_bytes_in = curr_bytes_in;
		prev_bytes_out = curr_bytes_out;

		curr_time = get_test_time();
		curr_bytes_in = get_total_bytes_in();
		curr_bytes_out = get_total_bytes_out();

		diff_time = curr_time - prev_time;
		diff_bytes_in = curr_bytes_in - prev_bytes_in;
		diff_bytes_out = curr_bytes_out - prev_bytes_out;

                curr_test_time = get_test_time();

		if (diff_time != 0.0)
		{
			rate_in = (diff_bytes_in/diff_time*8.0/1000000.0);
			rate_out = (diff_bytes_out/diff_time*8.0/1000000.0);
			printf("%f %g %g %lld %lld\n", curr_time, rate_in, rate_out, curr_bytes_in, curr_bytes_out);
                        fflush(stdout);
		}
		usleep(sample_period_us);
	}
}

void wait_for_start_signal()
{
	struct timespec ts;
	struct timeval tv;
	int retval;

	gettimeofday(&tv, NULL);
	ts.tv_sec = tv.tv_sec + 1;
	ts.tv_nsec = tv.tv_usec * 1000;
	do {
		ts.tv_sec += 1;
		pthread_mutex_lock(&start_signal_mutex);
		retval = pthread_cond_timedwait(&start_signal, &start_signal_mutex, &ts);
		pthread_mutex_unlock(&start_signal_mutex);
	} while (retval != 0 && !interrupted);
}

void send_start_signal()
{
	pthread_mutex_lock(&start_signal_mutex);
	pthread_cond_signal(&start_signal);
	pthread_mutex_unlock(&start_signal_mutex);
}

long long get_total_bytes_in()
{
	long long retval;
	pthread_mutex_lock(&total_bytes_in_mutex);
	retval = total_bytes_in;
	pthread_mutex_unlock(&total_bytes_in_mutex);
	return retval;
}

long long get_total_bytes_out()
{
	long long retval;
	pthread_mutex_lock(&total_bytes_out_mutex);
	retval = total_bytes_out;
	pthread_mutex_unlock(&total_bytes_out_mutex);
	return retval;
}

void add_to_total_bytes_in(long long val)
{
	pthread_mutex_lock(&total_bytes_in_mutex);
	total_bytes_in += val;
	pthread_mutex_unlock(&total_bytes_in_mutex);
}

void add_to_total_bytes_out(long long val)
{
	pthread_mutex_lock(&total_bytes_out_mutex);
	total_bytes_out += val;
	pthread_mutex_unlock(&total_bytes_out_mutex);
}

void handleint(int signum)
{
  interrupted = 1;
}

int read_ushort(char *str, unsigned short *val)
{
  char *endptr;
  int tmp_int;
	tmp_int = strtol(str, &endptr, 10);
	*val = (unsigned short)tmp_int;
  return ((*endptr == '\0') && (*val == tmp_int));
}

int read_int(char *str, int *val)
{
  char *endptr;
	*val = strtol(str, &endptr, 10);
  return (*endptr == '\0');
}

int read_uint(char *str, unsigned int *val)
{
  char *endptr;
	long long tmp_long_long;
	tmp_long_long = strtoll(str, &endptr, 10);
	*val = (unsigned int)tmp_long_long;
  return ((*endptr == '\0') && (*val == tmp_long_long));
}

int read_long_long(char *str, long long *val)
{
  char *endptr;
	*val = strtoll(str, &endptr, 10);
  return (*endptr == '\0');
}

int read_double(char *str, double *val)
{
  char *endptr;
	*val = strtod(str, &endptr);
  return (*endptr == '\0');
}

double get_current_time()
{
  struct timeval now;
  gettimeofday(&now, NULL);
  return (now.tv_sec + now.tv_usec/1000000.0);
}

void start_test_timer()
{
	test_start_time = get_current_time() + 1.0; // pause for one second before really starting
}

double get_test_time()
{
	return (get_current_time() - test_start_time);
}

