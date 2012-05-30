/*
 * packetcount.c: report time-synchronized packet count, starting on
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

int devfd = -1;
int cpufd = -1;

/* Open /proc/net/dev for reading packet counts */
void openstats() {
    devfd = open("/proc/net/dev", O_RDONLY);
    cpufd = open("/proc/stat", O_RDONLY);
    if (devfd < 0 || cpufd < 0) {
        perror("could not open device and cpu stats files");
        exit(1);
    }
}

/* Write time-stamped stats to buffer */
void readstats(double when, int fd) {
    int count = 1, written = 0, size = 0;
    // C: your buffer-overflowing friend
    assert(BUFSIZE - bufcount >= 0);
    count = snprintf(buffer + bufcount,
                     BUFSIZE - bufcount, "At %f seconds:\n", when);
    if (count < 0 || bufcount + count >= BUFSIZE) {
        bufcount = BUFSIZE;
        return;
    }
    bufcount += count + 1;
    lseek(fd, 0, SEEK_SET);
    while (count > 0 && bufcount < BUFSIZE) {
        assert(BUFSIZE - bufcount >= 0);
        count = read(fd, buffer + bufcount, BUFSIZE - bufcount);
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
    if (argc != 3) {
        fprintf(stderr, "usage: %s seconds interval\n", argv[0]);
        exit(1);
    }
    seconds = atoi(argv[1]);
    interval = atof(argv[2]);
    if (interval <= 0.0) {
        fprintf(stderr, "interval should be > 0\n");
        exit(1);
    }
    countdown = seconds/interval;
    openstats();
    starttimer(interval);
    while (countdown > 0) {
        double when;
        pause();
        when = now();
        /* Read packet counts */
        readstats(when, devfd);
        /* Read cpu stats */
        readstats(when, cpufd);
    }
    dumpstats();
    /* We let linux close our open files */
}
