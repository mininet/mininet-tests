#!/bin/bash

# Exit on any failure
#set -e

# Check for uninitialized variables
set -o nounset

ctrlc() {
	killall -9 python
	mn -c
	exit
}

trap ctrlc SIGINT
source ../tracing/trace.sh
trace_init

start=`date`
exptid=`date +%b%d-%H:%M`

rootdir=buffersizing-$exptid
plotpath=../util
iperf=~/iperf-patched/src/iperf

iface=s0-eth1

for run in 1; do
#for flows_per_host in 1 2 5 10 20 30 40 50 75 100 125 150 175 200 225 250 275 300 325 350 375 400; do
for flows_per_host in 1 2 5 10 50 100 200 300 400; do
#for flows_per_host in 1; do
	dir=$rootdir/nf$flows_per_host-r$run
  mkdir -p $dir

  #trace_start $dir/mntrace
	python buffersizing.py --bw-host 1000 \
		--bw-net 62.5 \
		--delay 43.5 \
		--dir $dir \
		--nflows $flows_per_host \
		-n 3 \
		--iperf $iperf
  #trace_stop $dir/mntrace
  #grep mn_ $dir/mntrace >  $dir/mntrace_trimmed


# was:		--use-bridge

	python $plotpath/plot_queue.py -f $dir/qlen_$iface.txt -o $dir/q.png
	python $plotpath/plot_tcpprobe.py -f $dir/tcp_probe.txt -o $dir/cwnd.png --histogram
done
done

cat $rootdir/*/result.txt | sort -n -k 1
python plot-results.py --dir $rootdir -o $rootdir/result.png
echo "Started at" $start
echo "Ended at" `date`
