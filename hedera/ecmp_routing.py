#!/usr/bin/python

"""
ecmp_routing.py: run ECMP routing expts on a fat-tree and a non-blocking topology

Nikhil Handigol
"""

import sys
sys.path = ['../'] + sys.path

import os
import random
import json
from time import sleep
from optparse import OptionParser
from subprocess import Popen, PIPE
import multiprocessing
import termcolor as T

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSKernelSwitch, CPULimitedHost
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info, warn, error, debug
from mininet.util import custom, quietRun, run

from util.monitor import monitor_cpu, monitor_devs_ng
from dctopo import FatTreeTopo
from NonBlockingTopo import NonBlockingTopo

# Parse command line options and dump results
def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-o', '--outputdir', dest='outputdir',
        default='/tmp', help='write output to file' )
    parser.add_option( '-i', '--infile', dest='infile',
        default=None, help='traffic gen input file' )
    parser.add_option( '-r', '--runs', dest='runs',
        type='int', default=1, help='specify number of runs of each test' )
    parser.add_option( '-b', '--bw', dest='bw', 
        type='int', default=0, help='use bandwidth limiting' )
    parser.add_option( '-p', '--cpu', dest='cpu', 
        type='float', default=-1, help='cpu fraction to allocate to each host' )
    parser.add_option( '-s', '--static', dest='static',
                      default=False, action='store_true',
                      help='statically allocate CPU to each host' )
    parser.add_option( '-t', '--time', dest='time', 
        type='int', default=30, help='duration for which to run the experiment' )
    parser.add_option( '-q', '--queue', dest='queue', 
        type='int', default=100, help='set switch buffer sizes' )
    parser.add_option( '-d', '--dctcp', dest='dctcp',
                      default=False, action='store_true',
                      help='use DCTCP' )
    parser.add_option( '-n', '--nonblocking', dest='nonblocking',
                      default=False, action='store_true',
                      help='Run the test on the nonblocking topo instead of fattree' )
    ( options, args ) = parser.parse_args()
    return options, args

opts, args = parseOptions()

def FatTreeNet(k=4, bw=100, cpu=-1,  queue=100):
    "Convenience function for creating pair networks"
    global opts

    pox_c = Popen("~/pox/pox.py --no-cli riplpox.riplpox --topo=ft,%s --routing=st --mode=proactive 1> %s/pox.out 2> %s/pox.out" % (k, opts.outputdir, opts.outputdir), shell=True)

    topo = FatTreeTopo(k, speed=bw/1000.)
    host = custom(CPULimitedHost, cpu=cpu)
    link = custom(TCLink, bw=bw, max_queue_size=queue)
	                      
    net = Mininet(topo, host=host, link=link, 
	    switch=OVSKernelSwitch, controller=RemoteController, 
	    autoPinCpus=opts.static, autoStaticArp=True)
    return net, pox_c

def NonBlockingNet(k=4, bw=100, cpu=-1, queue=100):
    "Convenience function for creating a non-blocking network"

    topo = NonBlockingTopo(k)
    host = custom(CPULimitedHost, cpu=cpu)
    link = custom(TCLink, bw=bw, max_queue_size=queue)
	                      
    net = Mininet(topo, host=host, link=link, 
	    switch=OVSKernelSwitch, controller=Controller, 
	    autoPinCpus=opts.static, autoStaticArp=True)
    return net

# iperf test for host pairs

#XXX - begin
#duplicate code, must go once the unify_test branch is merged in

def progress(t):
    while t > 0:
	print T.colored('  %3d seconds left  \r' % (t), 'cyan'),
	t -= 1
	sys.stdout.flush()
	sleep(1)
    print '\r\n'

def hostArray( net ):
    "Return array[1..N] of net.hosts"
    try:
	host_array = sorted(net.hosts, key=lambda x: int(x.name))
    except:
	host_array = sorted(net.hosts, key=lambda x: x.name)
    return host_array

def enable_tcp_ecn():
    Popen("sysctl -w net.ipv4.tcp_ecn=1", shell=True).wait()

def disable_tcp_ecn():
    Popen("sysctl -w net.ipv4.tcp_ecn=0", shell=True).wait()

def enable_dctcp():
    Popen("sysctl -w net.ipv4.tcp_dctcp_enable=1", shell=True).wait()
    enable_tcp_ecn()

def disable_dctcp():
    Popen("sysctl -w net.ipv4.tcp_dctcp_enable=0", shell=True).wait()
    disable_tcp_ecn()

def trafficGenPairs(opts, hosts, net):
    traffic_gen = 'hedera/cluster_loadgen/loadgen'
    if not os.path.isfile(traffic_gen):
	error('The traffic generator (%s) doesn\'t exist. \ncd \
	hedera/cluster_loadgen; make')
	return
    listen_port = 12345
    sample_period_us = 1000000

    debug('** Debugging\n')
    for h in hosts:
        debug('%s\n' % h.name)
        debug('%s\n' % h.cmd('ifconfig'))
        debug('%s\n' % h.cmd('ip route show'))
        debug('%s\n' % h.cmd('arp -a'))

    # XXX: debuggging
    net.pingAll()

    info('** Starting load-generators\n')
    for h in hosts:
        info('%s\n' % h.name)
        tg_cmd = '%s -f %s -i %s -l %d -p %d 2&>1 > %s/%s.out &' % (traffic_gen, opts.infile, 
                h.defaultIntf(), listen_port, sample_period_us,
                opts.outputdir, h.name)
        debug('%s\n' % tg_cmd)
	h.cmd(tg_cmd)
    sleep(1)

    info('** Triggering load-generators\n')
    for h in hosts:
        h.cmd('nc -nzv %s %d' % (h.IP(), listen_port))

    monitors = []

    monitors.append(multiprocessing.Process(target=monitor_cpu,
	args=('%s/cpu.txt' % opts.outputdir,)))
    monitors.append(multiprocessing.Process(target=monitor_devs_ng,
	args=('%s/txrate.txt' % opts.outputdir, 0.01)))

    for m in monitors:
	m.start()

    progress(opts.time)

    for m in monitors:
	m.terminate()

    info('** Stopping load-generators\n')
    for h in hosts:
	h.cmd('killall loadgen')

    # XXX: debuggging
    info('** Waiting for load-generators to finish\n')
    for h in hosts:
        info('%s\n' % h.name)
	os.system('cat %s/%s.out' % (opts.outputdir, h.name))

def FatTreeTest(opts):
    "run the traffic on a fat tree"
    k = 4
    bw = opts.bw if (opts.bw > 0) else None

    net, pox_c = FatTreeNet( k=k, cpu=opts.cpu, bw=bw, queue=opts.queue)
    net.start()
    hosts = hostArray( net )
    # wait for the switches to connect to the controller
    info('** Waiting for switches to connect to the controller\n')
    progress(5)

    trafficGenPairs(opts, hosts, net)
    net.stop()
    pox_c.terminate()

def NonBlockingTest(opts):
    "run the traffic on a non-blocking network"
    k = 4
    bw = opts.bw if (opts.bw > 0) else None

    net = NonBlockingNet( k=k, cpu=opts.cpu, bw=bw, queue=opts.queue)
    net.start()
    hosts = hostArray( net )
    # wait for the switches to connect to the controller
    sleep(1)

    trafficGenPairs(opts, hosts, net)
    net.stop()


# Run a set of tests
def HederaTest(opts):
    '''
    Run the ECMP and non-blocking experiments from the hedera paper
    '''
    if opts.nonblocking:
        # run the traffic on a non-blocking network
        NonBlockingTest(opts)
    else:
        # run the traffic on a fat tree
        FatTreeTest(opts)

def clean():
    '''Clean any running instances of POX'''
    p = Popen("ps aux | grep 'pox' | awk '{print $2}'",
	    stdout=PIPE, shell=True)
    p.wait()
    procs = (p.communicate()[0]).split('\n')
    for pid in procs:
	try:
	    pid = int(pid)
	    Popen('kill %d' % pid, shell=True).wait()
	except:
	    pass

if __name__ == '__main__':
    random.seed()
    setLogLevel( 'info' )

    if not os.path.isdir(opts.outputdir):
	os.makedirs(opts.outputdir)

    if opts.dctcp:
        enable_dctcp()

    clean()

    HederaTest(opts)

    disable_dctcp()

    Popen("killall -9 top bwm-ng", shell=True).wait()
    clean()
    os.system('sudo mn -c')
