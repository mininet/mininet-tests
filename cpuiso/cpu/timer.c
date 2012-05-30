#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/time.h>

typedef unsigned long long u64;
typedef struct timeval mytime_t;

char asked = 0;
u64 count = 0;

mytime_t start, interval, end, asked_delta, got_delta, latency;

mytime_t mk_time(long s, long us) {
  return (mytime_t){.tv_sec = s, .tv_usec = us};
}

mytime_t time_delta(mytime_t a, mytime_t b) {
  mytime_t ret;
#define M (1000000)
  unsigned del = (a.tv_sec - b.tv_sec)* M + (a.tv_usec - b.tv_usec);
  ret.tv_sec = del / M;
  ret.tv_usec = del % M;
  return ret;
}

void sighandler(int _) {
  gettimeofday(&end, NULL);
  got_delta = time_delta(end, start);
  latency = time_delta(got_delta, asked_delta);

  printf("%u\n", count);

#define P(a) a.tv_sec, a.tv_usec

  if(asked) {
    printf("%d.%06d,%d.%06d,%d.%06d\n", P(asked_delta), P(got_delta), P(latency));
    fprintf(stderr, "Asked delta: %d.%06d seconds\n", P(asked_delta));
    fprintf(stderr, "Got delta:   %d.%06d seconds\n", P(got_delta));
    fprintf(stderr, "Latency:     %d.%06d seconds\n", P(latency));
  }
  exit(0);
}

int main(int c, char *v[]) {
  signal(SIGTERM, sighandler);
  signal(SIGHUP, sighandler);
  signal(SIGINT, sighandler);
  signal(SIGALRM, sighandler);
  
  if(c > 2) {
    asked = 1;
    int del_s = atoi(v[1]);
    int del_us = atoi(v[2]);

    asked_delta = mk_time(del_s, del_us);
    interval = mk_time(0, 0);
    
    struct itimerval itimer = (struct itimerval){
      .it_value = asked_delta, 
      .it_interval = interval
    };
    
    gettimeofday(&start, NULL);
    setitimer(ITIMER_REAL, &itimer, NULL);
  }

  /* sleep indefinitely */
  while(1)
    sleep(100000);
  return 0;
}

