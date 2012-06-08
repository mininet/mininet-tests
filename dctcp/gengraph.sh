#!/bin/bash

bw=100
n=3

odir=results
mkdir -p $odir

hw_data=hw_data

for opts in "--cdf" ""; do
    tcp_odir=tcp-n$n-bw$bw
    dctcp_odir=dctcp-n$n-bw$bw
    sudo python ../util/plot_queue.py --maxy 40 -f $dctcp_odir/qlen_s1-eth1.txt $hw_data/q-dctcp-plot.txt -l Mininet-HiFi Hardware $opts -o $odir/dctcp$opts.pdf
    sudo python ../util/plot_queue.py -f $tcp_odir/qlen_s1-eth1.txt $hw_data/q-tcp-plot.txt -l Mininet-HiFi Hardware $opts -o $odir/tcp$opts.pdf
done

