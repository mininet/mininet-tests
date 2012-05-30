#!/bin/bash

NODES='2,5,10,20,40,60,80,100'
HOST=`hostname`

./plot_udpong.py -c $NODES results/$HOST/udping-{cfs,none}/

