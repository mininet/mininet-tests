//****************************************************************************/
// File:            common.h
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

#ifndef COMMON_H
#define COMMON_H
using namespace std;

/*
 * Standard C Libraries
 */
extern "C" {
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <net/if.h>
#include <netdb.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>
}

/*
 * C++ Libraries
 */
#include <vector>
#include <queue>

//****************************************************************************/
// Type Definitions
//****************************************************************************/

/*
 * Use this struct for making RPC requests of particular length and
 * delay.
 */
struct rpc_req_info
{
	long long response_length;
	double rpc_delay;
};

//****************************************************************************/
// Global (External) Variable Declarations
//****************************************************************************/

extern unsigned short listen_port; // FIXME: move this to server code
//extern unsigned int seed_init; // FIXME: Seems unnecessary
extern int verbosity;
extern volatile bool interrupted;
extern char *input_filename;	// FIXME: Remove this - should not be global
extern const char *net_interface; // does this have to be global
extern double curr_test_time;

//****************************************************************************/
// Global (External) Function Declarations
//****************************************************************************/

void client_init();  // FIXME: move this to client.h?
void *client_thread_main(void *arg);
void *server_thread_main(void *arg);
int read_double(char *str, double *val);
int read_ushort(char *str, unsigned short *val);
int read_int(char *str, int *val);
int read_uint(char *str, unsigned int *val);
int read_long_long(char *str, long long *val);
void start_test_timer();
double get_test_time();
double get_current_time();
void send_start_signal();
long long get_total_bytes_in();
long long get_total_bytes_out();
void add_to_total_bytes_in(long long val);
void add_to_total_bytes_out(long long val);

#endif

// vim: set ts=4 sw=4 expandtab:
