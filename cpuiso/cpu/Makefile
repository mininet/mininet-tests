
FILES=cpu-stress
FILES+=gettimeofday
FILES+=timer
FILES+=steal_cpu
FILES+=cpumonitor

all: $(FILES)
	@echo done

cpu-stress: cpu-stress.c
gettimeofday: gettimeofday.c
timer: timer.c

%.c:
	$(CC) $(CFLAGS) $< -o $@

.PHONY: clean
clean:
	rm $(FILES)

