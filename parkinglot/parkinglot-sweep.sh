#!/bin/bash

# Exit on any failure
set -e

# Check for uninitialized variables
set -o nounset

ctrlc() {
	sudo killall -9 python
	sudo mn -c
	exit
}

trap ctrlc SIGINT

start=`date`
exptid=`date +%b%d-%H:%M`
rootdir=parkinglot-$exptid
bw=100

# Note: you need to make sure you report the results
# for the correct port!
# In this example, we are assuming that each
# client is connected to port 2 on its switch.

for n in 1 2 3 4 5; do
    dir=$rootdir/n$n
    sudo python parkinglot.py --bw $bw \
        --dir $dir \
        -t 60 \
        -n $n
    sudo python ../util/plot_rate.py --rx \
        --maxy $bw \
        --xlabel 'Time (s)' \
        --ylabel 'Rate (Mbps)' \
        -i 's.*-eth2' \
        -f $dir/bwm.txt \
        -o $dir/rate.png
    sudo python ../util/plot_tcpprobe.py \
        -f $dir/tcp_probe.txt \
        -o $dir/cwnd.png
    sudo python ../util/plot_queue.py \
	-f $dir/qlen_s1-eth1.txt \
	-o $dir/qlen.png
done

echo "Started at" $start
echo "Ended at" `date`
echo "Output saved to $rootdir"
