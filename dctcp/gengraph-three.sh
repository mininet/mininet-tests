#!/bin/bash

# Generates the inter-dequeue time graphs.
# Please modify to pass in the right files.

bws="100 1000"
bws="10"
odir=plots
# for data on nf-build2_bw:
#iface=sw0-eth1
# for data on rhone w/latest cs244:
iface=s1-eth1

function gendata {
    for bw in $bws; do
      #file=~nikhilh/nf-build2_bw${bw}_mntrace
      file=tcp-n3-bw${bw}/mntrace
      mkdir -p $odir/bw$bw
      python ../tracing/parse.py -f $file --start 10 --end 12 \
               --intf $iface --output_link_data linkdata-$bw --logscale \
               --plots links,linkwindow --odir $odir/bw$bw
    done
}

gendata

python verify/link_dequeues.py --files linkdata-10 linkdata-100 linkdata-1000 \
         --expected  1211 121.1 12.11 \
         --labels "10Mb/s" "100Mb/s" "1Gb/s" \
         --title "" --ccdf --log --out output.pdf --percent
