#!/bin/bash

# Generates the inter-dequeue time graphs.
# Please modify to pass in the right files.

bws="100 1000"
dir=plots
iface=sw0-eth1

function gendata {
    for bw in $bws; do
      file=~nikhilh/nf-build2_bw${bw}_mntrace
      mkdir -p $dir/bw$bw
      python ../tracing/parse.py -f $file --start 10 --end 12 \
               --intf $iface --output_link_data linkdata-$bw --logscale \
               --plots links,linkwindow --odir $dir/bw$bw
    done
}

#gendata

python link_dequeues.py --files linkdata-100 linkdata-1000 \
         --expected  121.1 12.11 \
         --labels "100Mb/s" "1Gb/s" \
         --title "" --ccdf --log --out output.pdf --percent

