
#include <stdio.h>
#include <time.h>
#include <sys/time.h>
#include <signal.h>

int sometime_us;
int period_us;
volatile int start, blast, end;

inline struct timeval mk_time(int s, int us) {
  return (struct timeval){.tv_sec = s, .tv_usec=us};
}

void set_us_timer(int s, int us) {
  struct itimerval itimer = (struct itimerval){
    .it_value = mk_time(s, us), 
    .it_interval = mk_time(0, 0)
  };
  setitimer(ITIMER_REAL, &itimer, NULL);
}

/*
  initially, we run for sometime < quantum, then 
  sleep.  then we wake up at period - sometime and 
  run for sometime, then sleep, and repeat
*/

void sighandler(int _) {
  if(blast) {
    end = clock();
    printf("User elapsed: %0.6f\n", (end - start) * 1.0/ CLOCKS_PER_SEC);
    exit(0);
  }

  if(!(start & 1)) {
    set_us_timer(0, period_us - 2*sometime_us);
  } else {
    set_us_timer(0, 2*sometime_us);
  }
  start++;
}

void blaster(int _) {
  printf("Blasting!\n");
  blast = 1;
}

int main(int c, char *v[]) {
  if(c <= 1) return fprintf(stderr, "Usage: %s period (us)\n", v[0]);
  struct timespec a;
  a.tv_sec = 0;
  a.tv_nsec = atoi(v[1]) * 1000;
  
  period_us = atoi(v[1]);
  sometime_us = period_us / 10;
  
  start = 0;
  signal(SIGALRM, sighandler);
  signal(SIGINT, blaster);

  set_us_timer(0, sometime_us);
  while(!blast) {
    if(start & 1) {
      nanosleep(&a,&a);
    } else {
      while(!(start & 1));
    }
  }
  printf("Hogging CPU for 5s..\n");
  set_us_timer(5, 0);
  start = clock();
  while(1);
  return 0;
}

