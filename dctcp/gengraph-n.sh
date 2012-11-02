#!/bin/bash
# Exit on any failure
set -e

# Check for uninitialized variables
set -o nounset


# Generates the inter-dequeue time graphs.
# Please modify to pass in the right files.

bws="10 20 40 80 160 320 640 1280"
#bws="1280"
odir=plots
# for data on nf-build2_bw:
#iface=sw0-eth1
# for data on rhone w/latest cs244:
iface=s1-eth1
expt=dctcp

function gendata {
    for bw in $bws; do
      #file=~nikhilh/nf-build2_bw${bw}_mntrace
      file=$expt-n3-bw${bw}/mntrace
      mkdir -p $odir/bw$bw
      python ../tracing/parse.py -f $file --start 10 --end 12 \
               --intf $iface --output_link_data ${expt}-linkdata-$bw --logscale \
               --plots links,linkwindow --odir $odir/bw$bw
    done
}

gendata

files=
expecteds=
labels=
for bw in $bws; do
    files="$files ${expt}-linkdata-$bw"
    time_input=`./max_pkt_time.py $bw`
    expecteds="$expecteds ${time_input}"
    labels="$labels ${bw}Mb/s" 
done

echo "files: $files"
echo "expecteds: $expecteds"
echo "labels: $labels"

python verify/link_dequeues.py --files $files \
         --expected $expecteds \
         --labels $labels \
         --title "" --ccdf --log --out ${expt}-output.pdf --percent
