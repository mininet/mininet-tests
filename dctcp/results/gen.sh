#!/bin/bash

pq="python ../../util/plot_queue.py"

for opts in "--cdf" ""; do
	$pq  -f qlen-mn-dctcp.txt q-dctcp-plot.txt -l Mininet-HiFi Hardware $opts -o dctcp$opts.pdf --maxy 40 --every 5
	$pq  -f qlen-mn-tcp.txt q-tcp-plot.txt -l Mininet-HiFi Hardware $opts -o tcp$opts.pdf --maxy 600
done

