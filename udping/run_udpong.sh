#!/bin/bash
loaded=
up='sudo python udpong.py'

PLATFORM=`hostname` # was: nf-build2

#NODES='2 5 10 20 30 40 50 60 80 100 150 200 250 300 350 400 450 500'
#NODES='2 5 10 20'
NODES='2 5 10 20 40 60 80 100'


function run {
    echo $*
    time bash -c "$*"
}

for N in $NODES; do

for bw in cfs none; do 

    RESULTS_DIR=results/$PLATFORM/udping-$bw$loaded
    mkdir -p ${RESULTS_DIR}
    run $up $loaded --b $bw -c $N -o $RESULTS_DIR
    sleep 3
    sudo mn -c
done

done
