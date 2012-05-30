
FILES=packetcount

all: $(FILES)
	@echo done

udping: udping.c

%.c:
	$(CC) $(CFLAGS) $< -o $@

.PHONY: clean
clean:
	rm $(FILES)

