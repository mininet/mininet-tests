#!/usr/bin/env python
'''
Sweep over a number of hosts and max CPU utilizations, looking at CPU 
scheduling variance.
'''

from optparse import OptionParser
from time import sleep, time

from mininet.log import lg, setLogLevel, info, warn, output
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from CPUIsolationLib import (
    floatListCallback, intListCallback,
    sanityCheck,
    CPUIsolationTopo, CPUIsolationHost,
    initOutput, parse_cpuacct, appendOutput )
from mininet.util import quietRun, run, numCores, custom

CPUSTRESS = 'cpu/cpu-stress'
CPUMONITOR = 'cpu/cpumonitor'

def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-o', '--output',
        default=True,
        action='store_true',
        help='write output to file?' )
    parser.add_option( '-t', '--time',
        type='int',
        default=10,
        help='cpu-stress time interval' )
    parser.add_option( '-r', '--runs',
        type='int',
        default=1,
        help='Runs for each topo' )
    parser.add_option( '-c', '--counts',
        action='callback',
        callback=intListCallback,
        default=[ 2, 4 ],
        type='string',
        help='nodes in the network, e.g. 2,4' )
    parser.add_option( '-u', '--utils',
        action='callback',
        callback=floatListCallback,
        default=[ 0.5, 0.7, .9 ],
        type='string',
        help='target machine utilizations, e.g. .5,.7,.9' )
    parser.add_option( '-m', '--machine',
        default='local',
        type='string',
        help='name of machine' )
    parser.add_option( '-e', '--experiment',
        default='',
        type='string',
        help='name of experiment' )   
    parser.add_option( '-s', '--static',
        default=False,
        action='store_true',
        help='statically allocate CPU to each host' )
    parser.add_option( '-b', '--bwsched', dest='sched',
                       default='cfs',
                       help='bandwidth scheduler: cfs (default) | rt | none' )
    options, args = parser.parse_args()
    if options.sched not in [ 'cfs', 'rt', 'none' ]:
        print "CPU bandwidth scheduler should be either 'cfs' or 'rt' or 'none'."
        parser.print_help()
        exit( 1 )
    options.host = quietRun( 'hostname' ).strip()
    options.cores = numCores()
    return options, args


def appendResults(net, outfile, n, cpu):
    result = [''] * n
    cmd = [None] * n  # Command objects for CPU stressers
    monitor = [None]*n
    monitor_outfile = [None]*n  # Filenames
    cpu_log = [None]*n

    info ("Starting CPU stressors\n")
    # Start cpu-stressers
    for i in xrange(0, n):
        server = net.hosts[i]
        # run for 120 secs extra; terminated below
        scmd = '%s %d %d' % (CPUSTRESS, opts.time+120, 0) 
        server.cmd(scmd + '&')
        monitor_outfile[i] = '/tmp/%s_cpu.out' % server.name
    sleep(1)

    info ("Starting CPU monitor\n")
    # Start cpu monitor
    startTime = int(time())
    cpumon_length = opts.time
    # Was always one second.
    # Now we will try the following: since cpuacct is adjusted every
    # 10 ms, we should try to make sure that each process makes some
    # progress each time interval.
    # for a minimum cpu time of 20 ms,
    # the interval should be 20 ms * n / (cpu% * numCores())
    cpumon_interval = 1.0
    cpumon_min = .020 / cpu / numCores()
    if cpumon_interval < cpumon_min:
        cpumon_interval = cpumon_min
        print "Adjusting cpumon_interval to %.2f seconds" % cpumon_interval
    hosts = ' '.join([h.name for h in net.hosts])
    stats = quietRun('%s %d %f %s' % (CPUMONITOR, cpumon_length, cpumon_interval, hosts))

    info ("Terminating processes\n")
    quietRun( 'pkill -9 -f ' + CPUSTRESS )

    # parse cpu monitor results
    info ("Parsing CPU monitor results\n")
    cpu_usage = parse_cpuacct(stats, cpulimit=cpu)

    appendOutput(outfile, cpu_usage)


def hostWithSched(sched):
    return lambda n, *args, **kwargs: Host(n, *args, sched=sched, **kwargs)

def CPUIsolationSweep(opts):
    "Check CPU isolation for various no. of nodes."
    outfile = None
    if opts.output:
        outfile_base = 'results/' + opts.machine + '/' + opts.experiment + '/'
        placement = 'static' if opts.static else 'dyn'
        filename = 'cpuiso-%s-%s-%s-%s.out' % (
            opts.host, opts.sched, opts.cores, placement )
        outfile = outfile_base + filename
    info("writing to file: %s\n" % outfile)
    initOutput( outfile, opts )

    i = 0
    for n in opts.counts:
        for util in opts.utils:
            for r in xrange(1, opts.runs+1):

                info('\n*****  Running CPU Test %i: %d nodes,'
                     ' max util = %0.3f, trial %d\n' % (i, n, util, r))

                # Split system utilization evenly across hosts
                cpu = util / float(n)
                
                host = custom(CPUIsolationHost, cpu=cpu, sched=opts.sched)
                net = Mininet(topo=CPUIsolationTopo(n),
                              host=host, autoPinCpus=opts.static)
                net.start()
                info('*** Running test\n')
                appendResults(net, outfile, n, cpu)
                net.stop()
                
                i+=1

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    sanityCheck()
    CPUIsolationSweep(opts)
