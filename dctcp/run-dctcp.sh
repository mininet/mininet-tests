#!/bin/bash

function tcp {
# 2 TCP sources
sudo python dctcp.py --bw 1000 --speedup-bw 1013.4 --maxq 1000 --dir tcp-n3-bw1000 -t 30 -n 3
sudo python ../util/plot_rate.py -f tcp-n3-bw1000/txrate.txt --rx -o tcp-n3-bw1000/rate.png
sudo python ../util/plot_queue.py -f tcp-n3-bw1000/qlen_s1-eth1.txt -o tcp-n3-bw1000/qlen.png
}

function ecn {
# 2 TCP-ECN sources
sudo python dctcp.py --bw 1000 --speedup-bw 1013.4 --maxq 1000 --dir tcpecn-n3-bw1000 -t 30 -n 3 --ecn
sudo python ../util/plot_rate.py -f tcpecn-n3-bw1000/txrate.txt --rx -o tcpecn-n3-bw1000/rate.png
sudo python ../util/plot_queue.py -f tcpecn-n3-bw1000/qlen_s1-eth1.txt -o tcpecn-n3-bw1000/qlen.png
}

function dctcp {
# 2 DCTCP sources
sudo python dctcp.py --bw 1000 --speedup-bw 1013.4 --maxq 1000 --dir dctcp-n3-bw1000 -t 30 -n 3 --dctcp
sudo python ../util/plot_rate.py -f dctcp-n3-bw1000/txrate.txt --rx -o dctcp-n3-bw1000/rate.png
sudo python ../util/plot_queue.py -f dctcp-n3-bw1000/qlen_s1-eth1.txt -o dctcp-n3-bw1000/qlen.png
}

tcp
ecn
dctcp
