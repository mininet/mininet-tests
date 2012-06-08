#!/bin/bash

PLATFORM=`hostname` # was: nf-build2
RESULTS_DIR="results/$PLATFORM/hedera"
RUNS=1
#QUEUES="$(seq 10 20 200)"
QUEUES="50"

for q in $QUEUES;
do
    sudo python plot_ecmp_routing.py -r $RUNS -b 10 -m hedera/traffic_to_input.csv -i $RESULTS_DIR -s -10mbps-q$q hedera/hedera_results.csv
done
