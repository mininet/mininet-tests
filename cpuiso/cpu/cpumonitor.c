/*
 * cpumonitor.c: report time-synchronized cgroup CPU utilization, starting on
 *                the next one second tick.
*/


#include <sys/time.h>
#include <stdio.h>
#include <signal.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <assert.h>

/* Current time in seconds */
double now() {
    struct timeval tv;
    gettimeofday( &tv, NULL );
    return 1e-6 * tv.tv_usec + tv.tv_sec;
}

int countdown;

void handler( int sig ) {
    countdown--;
    if (countdown <= 0) {
        // We're done, so turn off timer
        signal(SIGALRM, SIG_IGN);
    }
    return; 
}

/* start a timer which goes off at 1-second ticks */
void starttimer(float interval) {
    struct timeval tv;
    struct itimerval itv;
    gettimeofday( &tv, NULL );
    itv.it_interval.tv_sec = interval;
    itv.it_interval.tv_usec = (interval - (int) interval) * 1000000;
    itv.it_value.tv_sec = 0;
    itv.it_value.tv_usec = 1000000 - tv.tv_usec;
    signal(SIGALRM, handler);
    setitimer(ITIMER_REAL, &itv, NULL);
}

enum { BUFSIZE=10000000 };
char buffer[BUFSIZE];
int bufcount = 0;

int *statfd= NULL;
int *usagefd= NULL;
int *percpufd= NULL;

/* Open cpuacct files for measuring cpu time */
#define OLDCGROUP "/cgroup/%s/"
#define CGROUP "/sys/fs/cgroup/cpuacct/%s/"
void openstats(const char *cgroup, int index) {
    char usage_fname[100], stat_fname[100], percpu_fname[100];
    sprintf(usage_fname, CGROUP "cpuacct.usage", cgroup);
    sprintf(stat_fname, CGROUP "cpuacct.stat", cgroup);
    sprintf(percpu_fname, CGROUP "cpuacct.usage_percpu", cgroup);
    usagefd[index] = open(usage_fname, O_RDONLY);
    statfd[index] = open(stat_fname, O_RDONLY);
    percpufd[index] = open(percpu_fname, O_RDONLY);
    if (statfd[index] < 0 || usagefd[index] < 0 || percpufd[index] < 0) {
        perror("could not open device and cpu stats files");
        exit(1);
    }
}

/* Write time-stamped stats to buffer */
void readstats(double when, const char *cgroup, int index) {
    int count = 1, written = 0, size = 0;
    // C: your buffer-overflowing friend
    assert(BUFSIZE - bufcount >= 0);
    count = snprintf(buffer + bufcount, 
                     BUFSIZE - bufcount, "cgroup %s,time %f\n", cgroup, when);
    if (count < 0 || bufcount + count >= BUFSIZE) {
        bufcount = BUFSIZE;
        return;
    }
    bufcount += count;
    // read total cpu usage
    assert(BUFSIZE - bufcount >= 0);
    count = snprintf(buffer + bufcount, 
                     BUFSIZE - bufcount, "usage ");
    if (count < 0 || bufcount + count >= BUFSIZE) {
        bufcount = BUFSIZE;
        return;
    }
    bufcount += count;
    count = 1;
    lseek(usagefd[index], 0, SEEK_SET);
    while (count > 0 && bufcount < BUFSIZE) {
        assert(BUFSIZE - bufcount >= 0);
        count = read(usagefd[index], buffer + bufcount, BUFSIZE - bufcount);
        if (count > 0) {
            bufcount += count;
        }
    }
    count = 1;
    lseek(statfd[index], 0, SEEK_SET);
    while (count > 0 && bufcount < BUFSIZE) {
        assert(BUFSIZE - bufcount >= 0);
        count = read(statfd[index], buffer + bufcount, BUFSIZE - bufcount);
        if (count > 0) {
            bufcount += count;
        }
    }
    count = 1;
    // read percpu usage
    assert(BUFSIZE - bufcount >= 0);
    count = snprintf(buffer + bufcount, 
                     BUFSIZE - bufcount, "percpu ");
    if (count < 0 || bufcount + count >= BUFSIZE) {
        bufcount = BUFSIZE;
        return;
    }
    bufcount += count;
    count = 1;
    lseek(percpufd[index], 0, SEEK_SET);
    while (count > 0 && bufcount < BUFSIZE) {
        assert(BUFSIZE - bufcount >= 0);
        count = read(percpufd[index], buffer + bufcount, BUFSIZE - bufcount);
        if (count > 0) {
            bufcount += count;
        }
    }
    if ( bufcount >= BUFSIZE) {
        fprintf( stderr, "*** BUFFER FILLED - results may be truncated\n" );
    }
}

/* Dump out statistics */
void dumpstats() {
    write(1, buffer, bufcount);
}


main(int argc, char *argv[]) {
    float seconds;
    float interval;
    int num_cgroups;
    int i;

    if (argc < 4) {
        fprintf(stderr, "usage: %s seconds interval [cgroups...]\n", argv[0]);
        exit(1);
    }
    seconds = atoi(argv[1]);
    interval = atof(argv[2]);
    num_cgroups = argc - 3;

    if (interval <= 0.0) {
        fprintf(stderr, "interval should be > 0\n");
        exit(1);
    }
    countdown = seconds/interval;
    usagefd = malloc(sizeof(int) * num_cgroups);
    statfd = malloc(sizeof(int) * num_cgroups);
    percpufd = malloc(sizeof(int) * num_cgroups);
    for(i = 0; i < num_cgroups; i++) {
        openstats(argv[3+i], i);
    }
    starttimer(interval);
    while (countdown > 0) {
        double when;
        pause();
        when = now();
        for(i = 0; i < num_cgroups; i++) {
            /* Read cpu stats */
            readstats(when, argv[3+i], i);
        }
    }
    dumpstats();
    /* We let linux close our open files */
}
