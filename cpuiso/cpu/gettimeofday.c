#include <stdio.h>
#include <sys/time.h>

typedef struct timeval mytime_t;

mytime_t start, end, temp;

int main(int c, char *v[]) {
  int runs = 100000, i = 0;
  if(c > 1) {
    runs = atoi(v[1]);
  }

  gettimeofday(&start, NULL);
  while(i++ < runs) {
    gettimeofday(&temp, NULL);
  }
  gettimeofday(&end, NULL);
  
  int diff = (end.tv_sec - start.tv_sec) * 1000000;
  diff += (end.tv_usec - start.tv_usec);
  
  printf("%f\n", diff*1.0/runs);
  return 0;
}

