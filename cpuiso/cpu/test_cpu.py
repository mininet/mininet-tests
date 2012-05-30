
import sys
sys.path = ['/home/jvimal/mininet'] + sys.path

from util import Command


MIN = 10000
ratios = xrange(2, 10+1)


def container_start(name, quota, period, program):
  cmd = [
    "lxc-execute",
    "-n", name, 
    "-s", "lxc.cgroup.cpuset.cpus=0",
    "-s",  "lxc.cgroup.cpu.cfs_quota_us=%d" % quota, 
    "-s", "lxc.cgroup.cpu.cfs_period_us=%d" % period,
  ] + program.split(' ')
  
  return Command(cmd).read_full()

for denom in ratios:
  print '###### CPU ratio: %d/%d ######' % (1, denom)
  for mul in [1, 2, 5, 10]:
    quota = mul * MIN
    period = denom * quota
    print "----- quota=%d, period=%d, 10second run -----" % (quota, period)
    print container_start("foo", quota, period, "./cpu-stress 10 0")
    sys.stdout.flush()
