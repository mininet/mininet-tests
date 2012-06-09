#!/bin/bash


nodes='A B C D E F G H I J '
others='C D E F G H I J'
bash=sh

function clean {
  node=$1
  echo "*** cleaning $node"
  ssh $node killall -9 $bash > /dev/null 2>&1
  # ssh $node ps ax
}

function ssh_bg {
  ssh $* < /dev/null > /dev/null 2>&1 &
}

function waste {
  cmd="'while true; do a=1; done'"
  echo "*** wasting time on $1"
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  ssh_bg $1 $bash -c $cmd 
  # ssh $1 ps x
}

function do_others {
  for node in $others; do
    $* node-$node
  done
} 

function do_many {
  echo "*** running $1 on $2 nodes"
  i=0
  limit=$2
  for x in $others $others; do
   if [ $i -ge $limit ]; then
     break
   fi
   $1 node-$x
   i=$(($i + 1))
  done
}

function iperf_test {
  for load in 0 1 2 3 4 5 6 7 8; do
    do_many waste $load
    echo "*** running iperf client with $load load processes" 
    iperf -i6 -t60 -c node-B-0
    do_many clean $load
  done
}


echo "*** starting up"
  clean node-B
  do_others clean
echo "*** starting iperf server"
  ssh node-B iperf -s < /dev/null > /tmp/iperf.out 2>&1 &
  sleep 5
echo "*** running iperf test"
  iperf_test
echo "*** shutting down"
  ssh node-B killall iperf
  do_others clean
  wait
  jobs
echo "*** printing server output"
  cat /tmp/iperf.out
echo "*** test complete"
exit
