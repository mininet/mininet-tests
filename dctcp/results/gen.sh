#!/bin/bash

pq="python ../../util/plot_queue.py"

for opts in "--cdf" ""; do
	$pq  -f qlen-mn-dctcp.txt q-dctcp-plot.txt -l Mininet-Hifi Hardware $opts -o dctcp$opts.pdf --maxy 40
	$pq  -f qlen-mn-tcp.txt q-tcp-plot.txt -l Mininet-Hifi Hardware $opts -o tcp$opts.pdf --maxy 500
done

