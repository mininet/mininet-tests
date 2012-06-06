CC=g++
CFLAGS=-Wall -O3 -g
LFLAGS=-pthread

loadgen: main.o server.o client.o
	$(CC) $(LFLAGS) main.o server.o client.o -o $@

main.o: main.cc common.h
	$(CC) -c $(CFLAGS) main.cc -o $@

server.o: server.cc common.h
	$(CC) -c $(CFLAGS) server.cc -o $@

client.o: client.cc common.h
	$(CC) -c $(CFLAGS) client.cc -o $@

clean:
	rm -rf loadgen *.o

