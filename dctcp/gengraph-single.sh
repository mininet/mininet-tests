#!/bin/bash

# Generates the inter-dequeue time graphs.
# Please modify to pass in the right files.

bws="100 1000"
bws="100"
odir=plots
# for data on nf-build2_bw:
#iface=sw0-eth1
# for data on rhone w/latest cs244:
iface=s1-eth1

function gendata {
    for bw in $bws; do
      #file=~nikhilh/nf-build2_bw${bw}_mntrace
      file=Oct30-12\:21/tcp-n3-bw100/mntrace
      mkdir -p $odir/bw$bw
      python ../tracing/parse.py -f $file --start 10 --end 12 \
               --intf $iface --output_link_data linkdata-$bw --logscale \
               --plots links,linkwindow --odir $odir/bw$bw
    done
}

gendata

#python link_dequeues.py --files linkdata-100 linkdata-1000 \
#         --expected  121.1 12.11 \
#         --labels "100Mb/s" "1Gb/s" \
#         --title "" --ccdf --log --out output.pdf --percent
#

# Single bandwidth
python verify/link_dequeues.py --files linkdata-100 \
         --expected  121.1 \
         --labels "100Mb/s" \
         --title "" --ccdf --log --out output-bw$bw.pdf --percent

