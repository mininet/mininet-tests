#!/bin/bash

PLATFORM=`hostname` # was: nf-build2
RESULTS_DIR="results/$PLATFORM/hedera"
INPUT_DIR=hedera/inputs
RUNS=1
#RUNS=$(seq 4 5)
#QUEUES="$(seq 10 20 200)"
QUEUES="50"
INFILES='stag_prob_0_2_3_data stag_prob_1_2_3_data stag_prob_2_2_3_data stag_prob_0_5_3_data stag_prob_1_5_3_data stag_prob_2_5_3_data stride1_data stride2_data stride4_data stride8_data random0_data random1_data random2_data random0_bij_data random1_bij_data random2_bij_data random_2_flows_data random_3_flows_data random_4_flows_data hotspot_one_to_one_data'

function nonblocking_sweep {
for q in $QUEUES;
do
    for i in $(seq $RUNS);
    #for i in $RUNS;
    do
        for f in $INFILES;
        do
            infile=$INPUT_DIR/$f
            traffic=$(basename $infile)
            pref="nonblocking-10mbps-q$q"
            nonblocking_outdir=$RESULTS_DIR/$pref/$i/$traffic

            mkdir -p $nonblocking_outdir
            echo "sudo python ecmp_routing.py -n -b 10 -s -p 0.03 -q $q -i $infile -o $nonblocking_outdir"
            sudo python ecmp_routing.py -n -b 10 -s -p 0.03 -q $q -i $infile -o $nonblocking_outdir
        done
    done
done
}

function fattree_sweep {
for q in $QUEUES;
do
    for i in $(seq $RUNS);
    #for i in $RUNS;
    do
        for f in $INFILES;
        do
            infile=$INPUT_DIR/$f
            traffic=$(basename $infile)
            pref="fattree-10mbps-q$q"
            fattree_outdir=$RESULTS_DIR/$pref/$i/$traffic

            mkdir -p $fattree_outdir
            echo "sudo python ecmp_routing.py -b 10 -s -p 0.03 -q $q -i $infile -o $fattree_outdir"
            sudo python ecmp_routing.py -b 10 -s -p 0.03 -q $q -i $infile -o $fattree_outdir
        done
    done
done
}

nonblocking_sweep
fattree_sweep
