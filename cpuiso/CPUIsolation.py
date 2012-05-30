#!/usr/bin/env python

from optparse import OptionParser
from time import sleep, time

from mininet.log import lg, setLogLevel, info, warn, output
from mininet.net import Mininet
from mininet.topo import SingleSwitchTopo
from CPUIsolationLib import ( CPUIsolationHost, CPUIsolationTopo,
                              sanityCheck,
                              intListCallback, initOutput, parse_cpuacct,
                              appendOutput )
from mininet.util import quietRun, numCores, custom
from mininet.cli import CLI

def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-o', '--output', dest='outfile',
        default=None, help='write output to file' )
    parser.add_option( '-t', '--time', dest='time',
        type='int', default=10, help='select cpu-stress time interval' )
    parser.add_option( '-r', '--runs', dest='runs',
        type='int', default=1, help='No. of runs for each topo' )
    parser.add_option( '-u', '--util', dest='cpu',
        type='float', default=.5, help='fraction of entire system to use (.5)' )
    parser.add_option( '-i', '--bwinterval', dest='period',
                      type='int', default=100000, 
                      help='bw enforcement interval in microseconds' )
    parser.add_option( '-c', '--counts', dest='counts',
        action='callback', callback=intListCallback, default=[ 1 ],
        type='string',
        help='specify pair counts, e.g. 10,20,40' )
    # Disabled until we fix for RT:
    # parser.add_option( '-n', '--numprocs', dest='numprocs',
    #    type='int', default=1, help='no. of cpu-stress processes in each host' )
    parser.add_option( '-s', '--static', dest='static',
                      default=False, action='store_true',
                      help='statically allocate CPU to each host' )
    parser.add_option( '-b', '--bwsched', dest='sched',
                       default='cfs',
                       help='bandwidth scheduler: cfs (default) | rt | none' )
    ( options, args ) = parser.parse_args()
    if options.sched not in [ 'cfs', 'rt', 'none' ]:
        print "CPU bandwidth scheduler should be 'cfs' or 'rt' or 'none'."
        parser.print_help()
        exit( 1 )
    options.host = quietRun( 'hostname' ).strip()
    options.cores = numCores()
    # Limited to 1 until we fix for RT:
    options.numprocs = 1
    return options, args


def CPUIsolationTest(opts):
    "Check CPU isolation for various no. of nodes."

    cpustress = 'cpu/cpu-stress'
    cpumonitor = 'cpu/cpumonitor'
    results = []
    initOutput( opts.outfile, opts )

    for n in opts.counts:
        for run in xrange(1, opts.runs+1):
            # divide target utilization across hosts
            cpu = opts.cpu / n
            print 'Running CPU Test: %d nodes, cpu=%.3f%%, trial no. %d' % (
                n, 100.0*cpu, run)
            host = custom(CPUIsolationHost, cpu=cpu,sched=opts.sched,
                          period_us=opts.period)
            net = Mininet(topo=CPUIsolationTopo(n),
                          host=host, autoPinCpus=opts.static)
            net.start()
            result = [''] * n
            cmd = [None] * opts.numprocs *n
            #monitor = [None]*n
            #monitor_outfile = [None]*n
            #cpu_log = [None]*n

            #start the cpu-stressers
            for i in xrange(0, n):
                server = net.hosts[i]
                # scmd = '%s %d %d' % (cpustress, opts.time+10, 0) # run for ten secs extra
                scmd = cpustress # run indefinitely!

                for j in range(opts.numprocs):
                    # was: cmd[j*n + i] = server.lxcSendCmd(scmd)
                    # Using shell for now since lxc-attach is broken for RT
                    cmd[j*n + i] = server.sendCmd(scmd)
                #monitor_outfile[i] = '/tmp/%s_cpu.out' % server.name
                #monitor[i] = start_monitor_cpu(server, monitor_outfile[i])
            sleep(1)

            # start the cpu monitor
            startTime = int(time())
            cpumon_length = opts.time
            # Was always one second.
            # Now we want the cpuacct timer to get a 10 ms tick,
            # even with minimum quota of 1 ms
            cpumon_interval = 1.0
            cpumon_min = .011 / (cpu * numCores() )
            if cpumon_interval < cpumon_min:
                cpumon_interval = cpumon_min
                print "Adjusting cpumon_interval to %.2f seconds" % cpumon_interval
            hosts = ' '.join([h.name for h in net.hosts])
            info('*** Running test and monitoring output\n')
            cmd = ( '%s %d %f %s' % 
                    (cpumonitor, cpumon_length, cpumon_interval, hosts) )
            stats = quietRun(cmd)
            # parse cpu monitor results
            cpu_usage = parse_cpuacct(stats, cpulimit=cpu)
            #fetch the results
            # BL: Ignore this for now to avoid shutdown effects!
            if False:
                for i in xrange(0, n):
                    server = net.hosts[i]
                    for j in range(opts.numprocs):
                        # was: c = cmd[j*n + i].waitOutput()
                        c = server.waitOutput()
                    #stop_monitor_cpu(server)
                    # sleep(0.5)
                    #cpu_log[i] = parse_cpu_log(monitor_outfile[i])
                    #quietRun('rm -rf %s' % monitor_outfile[i])
                    try:
                        result[i] = c.split('\n')[1].replace(',',':')
                    except:
                        result[i] = 'NaN'

                print ','.join(result)
            else:
                quietRun( 'pkill -9 ' + cpustress )
            #appendOutput(opts, cpu_log)
            appendOutput(opts.outfile, cpu_usage)
            net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    sanityCheck()
    CPUIsolationTest(opts)
