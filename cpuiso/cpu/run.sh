#!/bin/sh

container=`date +%s`
quota=100000
period=500000

#  -s lxc.cgroup.cpuset.cpus=$1 \
lxc-execute -n "$container" \
  -s  lxc.cgroup.cpu.cfs_quota_us=$quota \
  -s lxc.cgroup.cpu.cfs_period_us=$period \
  ./cpu-stress 36000 0
  #python timer_latency.py $quota-$period
  #./steal_cpu 500000

