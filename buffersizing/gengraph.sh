#!/bin/bash

# Plot inter-dequeue time distribution...

# Exit on any failure...
set -e

dir=buffersizing-Jun08-00:37 

nflows="10 100 400"
r=1

function gendata {
    for flow in $nflows; do
        echo $flow

        if ! [ -f $dir/nf$flow-r$r/mntrace_trimmed ]; then
          echo "unzipping..."
          gunzip $dir/nf$flow-r$r/mntrace_trimmed.gz
        fi

        python ../tracing/parse.py -f $dir/nf$flow-r$r/mntrace_trimmed --start 28 --end 30 \
          --intf s0-eth1 --output_link_data linkdata-$flow --logscale \
          --plots links,linkwindow --odir $dir/nf$flow-r$r/plots

        gzip $dir/nf$flow-r$r/mntrace_trimmed &
    done

    wait
}

#gendata

python link_dequeues.py --files linkdata-10 linkdata-100 linkdata-400 \
    --expected  193.8 193.8 193.8 \
    --labels "20 flows" "200 flows" "800 flows" \
    --title "" --ccdf --log --out output.pdf --percent

