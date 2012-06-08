#!/bin/bash

bw=100
t=120
n=3
maxq=425

function tcp {
# 2 TCP sources
odir=tcp-n$n-bw$bw
sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n
sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
sudo python ../util/plot_queue.py -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function ecn {
# 2 TCP-ECN sources
odir=tcpecn-n$n-bw$bw
sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --ecn
sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
sudo python ../util/plot_queue.py -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function dctcp {
# 2 DCTCP sources
odir=dctcp-n$n-bw$bw
sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --dctcp
sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
sudo python ../util/plot_queue.py --maxy 50 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

tcp
#ecn
dctcp
