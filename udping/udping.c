#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUFSIZE 1
#define PORT 32000

double diff_time(const struct timeval t1, const struct timeval t2)
{
    double t1_sec = (double)(t1.tv_sec + t1.tv_usec/(1000.0*1000.0));
    double t2_sec = (double)(t2.tv_sec + t2.tv_usec/(1000.0*1000.0));
    return (t1_sec - t2_sec);
}

int main(int argc, char**argv)
{
    int sockfd, n, i;
    int len;
    struct sockaddr_in servaddr,cliaddr;
    char sendline[BUFSIZE];
    char recvline[BUFSIZE];
    char str[INET_ADDRSTRLEN];
    int num_pings;
    struct timeval t1, t2;

    if (argc != 1 && argc != 3)
    {
        printf("usage:  udping <IP address> <numpings>\n");
        exit(1);
    }

    if(argc == 1) {
        //server

        sockfd=socket(AF_INET,SOCK_DGRAM,0);

        bzero(&servaddr,sizeof(servaddr));
        servaddr.sin_family = AF_INET;
        servaddr.sin_addr.s_addr=htonl(INADDR_ANY);
        servaddr.sin_port=htons(PORT);
        bind(sockfd, (struct sockaddr *)&servaddr, sizeof(servaddr));

        while(1) {
            len = sizeof(cliaddr);
            n = recvfrom(sockfd, recvline, BUFSIZE, 0, (struct sockaddr *)&cliaddr, &len);

            printf("-------------------------------------------------------\n");
            inet_ntop(AF_INET, &(cliaddr.sin_addr), str, INET_ADDRSTRLEN);
            printf("Received ping from: %s\n", str);

            sendto(sockfd, recvline, BUFSIZE, 0, (struct sockaddr *)&cliaddr, sizeof(cliaddr));
        }
    }

    else if(argc == 3) {
        //client
        sockfd=socket(AF_INET,SOCK_DGRAM,0);

        bzero(&servaddr, sizeof(servaddr));
        bzero(sendline, sizeof(sendline));
        servaddr.sin_family = AF_INET;
        servaddr.sin_addr.s_addr=inet_addr(argv[1]);
        servaddr.sin_port=htons(PORT);

        num_pings = atoi(argv[2]);
        for(i = 0; i < num_pings; i++) {
            gettimeofday(&t1, 0);
            sendto(sockfd, sendline, BUFSIZE, 0, (struct sockaddr *)&servaddr, sizeof(servaddr));
            n = recvfrom(sockfd, recvline, BUFSIZE, 0, NULL, NULL);
            gettimeofday(&t2, 0);
            printf("%g\n", diff_time(t2, t1));
        }
    }
}
