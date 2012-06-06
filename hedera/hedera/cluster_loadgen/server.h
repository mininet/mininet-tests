//****************************************************************************/
// File:            server.h
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

#ifndef SERVER_H
#define SERVER_H

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

/*
 * Project Headers
 */
#include "common.h"

using namespace std;

//****************************************************************************/
// Type Definitions
//****************************************************************************/

//****************************************************************************/
// Global (External) Variable Declarations
//****************************************************************************/

/*
 * This class encapsulates the all the data related to a single loadgen server
 * instance
 */
class Server : public EventHandler {

    private:

        /*
         * Constant fields that are specify the traffic_gen spec and are set once
         */
        /*
         *
         */
        struct sockaddr_in dstAddr;
        /*
         * Should the destination be randomly chosen?
         */
        bool destRandom;
        /*
         * Start time in seconds when this flow should be started
         */
        double startTime;
        /*
         * Stop time in seconds
         */
        double stopTime;
        /*
         * Type of the flow
         */
        trafficType type;
        /*
         * Size of the flow
         */
        long long flowSize;
        /*
         * Should the flow size be chosen randomly with flow_size as the average
         * size of the flow?
         */
        bool flowSizeRandom;
        /*
         * Number of repetitions before this traffic gen spec is terminated
         */
        long long repetitions;
        /*
         * Time between flow repetitions in seconds
         */
        double timeBetweenFlows;
        /*
         * Should the time between flow repetitions be random with
         * time_between_flows as the average size of the flow
         */
        bool time_between_flows_random;
        /*
         * Delay for RPC calls
         */
        double rpcDelay;
        /*
         * Should the RCP delay be chosen randomly with rpc_delay as the average
         * value?
         */
        bool rpcDelayRandom;
        /*
         * Dynamically changing fields
         */
        /*
         * Socket descriptor of the currently active flow of this traffic_gen
         * instance
         */
        int sock;
        /*
         * Number of bytes generated / transferred by this traffic_gen specification
         * This includes the bytes transferred across all repetitions of this
         * traffic_gen specification.
         */
        long long bytesTransferred;
        /*
         * Bytes that are still left to be transferred in this particular flow
         * repetition
         */
        long long bytesLeft;
        /*
         * Number of repetitions of this flow that are still left
         */
        long long repetitionsLeft;
        /*
         * Time when this flow's repetition should be started next time.
         * FIXME : This particular parameter might not be required. Check if it
         * can be removed. Also check if this has to be replaced with a
         * timestamp instead of time remaining before reset.
         */
        double nextStartTime;
        /*
         * Seed for the random number generator. This allows the workload to be
         * reproduced in the testbed as well as in the simulator
         */
        unsigned int seed;
        /*
         * Has an RPC request been sent?
         */
        bool rpcRequestSent;
        /*
         * Is this traffic_gen specifiction completed with its flows?
         */
        int done;

    public:
        Client();
        ~Client();
        int readHandler();
        int writeHandler();
}


//****************************************************************************/
// Global (External) Function Declarations
//****************************************************************************/

void client_init();  // move this to client.h?
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
