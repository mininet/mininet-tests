#!/bin/bash

for opts in "--cdf" ""; do
  plot_queue.py -f qlen-mn-dctcp.txt q-dctcp-plot.txt -l Mininet-Hifi Hardware $opts -o dctcp$opts.pdf
  plot_queue.py -f qlen-mn-tcp.txt q-tcp-plot.txt -l Mininet-Hifi Hardware $opts -o tcp$opts.pdf
done

