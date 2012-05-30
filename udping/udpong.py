#!/usr/bin/env python

from optparse import OptionParser
from time import sleep, time
import re
import os
from sys import stdout, path

path.append( '..' )

from mininet.log import lg, setLogLevel, info, warn, output
from mininet.net import Mininet
from mininet.node import CPULimitedHost, Controller
from cpuiso.CPUIsolationLib import ( cpuStressName, cpuMonitorName,
                                     checkForExec,
                                     intListCallback, parse_cpuacct )
#from CPUIsolationLib import initOutput, appendOutput
from mininet.util import quietRun, numCores, custom
from mininet.topo import Topo


def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-o', '--outdir', dest='outdir',
                       default='', help='write output to dir' )
    parser.add_option( '-c', '--counts', dest='counts',
                       action='callback', callback=intListCallback, default=[ 2 ],
                       type='string', help='specify node counts, e.g. 10,20,40' )
    parser.add_option( '-m', '--numprocs', dest='numprocs', type='int',
                       default=1,
                       help='Number of CPU stress processes per node' )
    parser.add_option( '-n', '--nonamespace', dest='nonamespace',
                      default=False, action='store_true',
                      help='don\'t run hosts in namespace' )
    parser.add_option( '-s', '--static', dest='static',
                      default=False, action='store_true',
                      help='statically allocate CPU to each host' )
    parser.add_option( '-b', '--bwcpu', dest='sched',
                      default='cfs', type='string',
                      help='CPU bandwidth limiting=cfs|rt|none' )
    parser.add_option( '-i', '--interval', dest='interval',
                       type='float', default=0.0,
                       help='time interval between successive pings' )
    parser.add_option ('-l', '--loaded', dest='loaded',
                       default=False, action='store_true',
                       help='also run cpu stress processes on client and server' )
    parser.add_option('-p', '--pings', dest='pings',
                      default=1000, type='int',
                      help='number of pings')
    parser.add_option('-e', '--period', dest='period',
                      default=100000, type='int',
                      help='enforcement period (us) for CPU bandwidth limiting')
    ( options, args ) = parser.parse_args()
    return options, args

class PingPongTopo(Topo):
    "Simple topology: N hosts but only one link"

    def __init__( self, N ):
        super( PingPongTopo, self ).__init__()

        # Create host nodes
        hosts = [ 'h%s' % i  for i in range(1, N+1) ]
        for h in hosts:
            self.add_host(h)

        self.add_link( hosts[0], hosts[1] )


def pingpongtest(opts):
    "UDP ping latency test"
    cpustress = cpuStressName()
    cpumonitor = cpuMonitorName()
    udping = checkForExec( 'udping', '.' )
    results = []
    #initOutput( opts.outfile, opts )
    if opts.outdir and not os.path.exists(opts.outdir):
        os.makedirs(opts.outdir)

    info('*** killing off any cpu stress processes\n')
    quietRun('pkill -9 -f %s > /dev/null' % cpustress)
    print quietRun('pgrep cpu')

    info( "*** running ping test" )
    opts.time = opts.pings

    for n in opts.counts:
        opts.cpu = 0.5 / n
        host = custom(CPULimitedHost, cpu=opts.cpu, 
                      inNamespace=(not opts.nonamespace),
                      sched=opts.sched,
                      period_us=opts.period)
        topo=PingPongTopo(n) 
        net = Mininet(topo=topo, host=host, autoPinCpus=opts.static)
        net.start()

        info('*** Starting cpu stress processes\n')
        cmd = {}
        # For the "loaded" configuration we run stress procs everywhere;
        # Otherwise they don't run on the udping client or server
        start = 1 if opts.loaded else 3
        for i in xrange(start, n+1):
            server = net.get( 'h%s' % i )
            scmd = cpustress
            for j in range(opts.numprocs):
                cmd[(i, j)] = server.popen(scmd)
            info('.')
        info('\n')

        # info('*** Waiting 10 seconds for cpu stress processes to stabilize\n')
        # sleep(10)

        info('*** Checking connectivity and creating OpenFlow route\n')
        h1, h2 = net.get( 'h1', 'h2' )
        h1.cmd('ping -nc%d %s' % (1, h2.IP()))

        info('*** Starting udping server and waiting 5 seconds\n')
        h2.cmd('%s > /dev/null &' % udping)
        sleep(5)

        info('*** Running udping client for %s pings\n' % opts.pings)
        start = time()
        pout = h1.cmd('%s %s %s' % (udping, h2.IP(), opts.pings))
        end = time()
        if opts.outdir:
            f = open( '%s/u-%d' % (opts.outdir, n), 'w' )
            print >>f, pout
            f.close()
        elapsed = end - start

        # Compute average ping latency and overall average ping time
        values = [float(s) for s in pout.splitlines()]
        avgnetms = sum(values)/len(values) * 1000.0
        info( '*** Average per-ping latency %.3f ms\n' % avgnetms )
        info('*** %s pings completed in %.3f seconds\n' % (opts.pings, elapsed ) )
        avgms  = (elapsed/opts.pings * 1000.0)
        info( '*** Average ping time overall: %.3f ms\n' % avgms )
        info('*** Stopping cpu stress processes and collecting output\n')
        result = {}
        quietRun( 'pkill -f ' + cpustress )
        for key, popen in cmd.iteritems():
            popen.terminate()
            info( '.' )
            result[ key ] = int( popen.communicate()[ 0 ] )
        info( '\n' )
        # Print sorted cpu stress output
        print "*** cpu stress process output:"
        print [ (key, result[key]) for key in sorted( result ) ]
        # Get rid of any stragglers
        print quietRun( 'pkill -9 -f ' + cpustress )
        info('*** Stopping updping')
        print quietRun( 'pkill -9 udping' )

        net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    pingpongtest(opts)

