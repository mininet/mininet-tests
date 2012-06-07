#!/usr/bin/python
import sys
sys.path = ['../'] + sys.path

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
import multiprocessing
from subprocess import Popen, PIPE
import re
import termcolor as T
import argparse

import os
from util.monitor import monitor_cpu, monitor_qlen, monitor_devs_ng

parser = argparse.ArgumentParser(description="DCTCP tester (Star topology)")
parser.add_argument('--bw', '-B',
                    dest="bw",
                    action="store",
                    help="Bandwidth of links",
                    required=True)

parser.add_argument('--dir', '-d',
                    dest="dir",
                    action="store",
                    help="Directory to store outputs",
                    required=True)

parser.add_argument('-n',
                    dest="n",
                    action="store",
                    help="Number of nodes in star.  Must be >= 3",
                    required=True)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    help="Seconds to run the experiment",
                    default=30)

parser.add_argument('-u', '--udp',
                    dest="udp",
                    action="store_true",
                    help="Run UDP test",
                    default=False)

parser.add_argument('--use-hfsc',
                    dest="use_hfsc",
                    action="store_true",
                    help="Use HFSC qdisc",
                    default=False)

parser.add_argument('--maxq',
                    dest="maxq",
                    action="store",
                    help="Max buffer size of each interface",
                    default=425)

parser.add_argument('--speedup-bw',
                    dest="speedup_bw",
                    action="store",
                    help="Speedup bw for switch interfaces",
                    default=-1)

parser.add_argument('--dctcp',
                    dest="dctcp",
                    action="store_true",
                    help="Enable DCTCP (net.ipv4.tcp_dctcp_enable)",
                    default=False)

parser.add_argument('--ecn',
                    dest="ecn",
                    action="store_true",
                    help="Enable ECN (net.ipv4.tcp_ecn)",
                    default=False)

parser.add_argument('--use-bridge',
                    dest="use_bridge",
                    action="store_true",
                    help="Use Linux Bridge as switch",
                    default=False)

parser.add_argument('--tcpdump',
                    dest="tcpdump",
                    action="store_true",
                    help="Run tcpdump on host interfaces",
                    default=False)

parser.add_argument('--delay',
	dest="delay",
	default="0.075ms  0.05ms distribution normal  ")

args = parser.parse_args()
args.n = int(args.n)
args.bw = float(args.bw)
if args.speedup_bw == -1:
    args.speedup_bw = args.bw
args.n = max(args.n, 2)

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

if args.use_bridge:
    from mininet.node import Bridge as Switch
else:
    from mininet.node import OVSKernelSwitch as Switch

lg.setLogLevel('info')

class StarTopo(Topo):

    def __init__(self, n=3, bw=100):
        # Add default members to class.
        super(StarTopo, self ).__init__()

        # Host and link configuration
        hconfig = {'cpu': -1}
	ldealay_config = {'bw': bw, 'delay': args.delay,
			'max_queue_size': 1000000
			} 
	lconfig = {'bw': bw, 
		   'max_queue_size': int(args.maxq),
		   'enable_ecn': args.ecn or args.dctcp,
		   'use_hfsc': args.use_hfsc,
		   'speedup': float(args.speedup_bw)
		}

        print '~~~~~~~~~~~~~~~~~> BW = %s' % bw

        # Create switch and host nodes
        for i in xrange(n):
            self.add_host('h%d' % (i+1), **hconfig)

        self.add_switch('s1',)

        self.add_link('h1', 's1', **lconfig)
        for i in xrange(1, n):
            self.add_link('h%d' % (i+1), 's1', **ldealay_config)

def waitListening(client, server, port):
    "Wait until server is listening on port"
    if not 'telnet' in client.cmd('which telnet'):
        raise Exception('Could not find telnet')
    cmd = ('sh -c "echo A | telnet -e A %s %s"' %
           (server.IP(), port))
    while 'Connected' not in client.cmd(cmd):
        output('waiting for', server,
               'to listen on port', port, '\n')
        sleep(.5)

def progress(t):
    while t > 0:
        print T.colored('  %3d seconds left  \r' % (t), 'cyan'),
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print '\r\n'

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

def main():
    seconds = int(args.t)
    # Reset to known state
    disable_dctcp()
    disable_tcp_ecn()
    if args.ecn:
        enable_tcp_ecn()
    if args.dctcp:
        enable_dctcp()
    topo = StarTopo(n=args.n, bw=args.bw)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, switch=Switch,
	    autoStaticArp=True)
    net.start()

    h1 = net.getNodeByName('h1')
    print h1.cmd('ping -c 2 10.0.0.2')
    h1.sendCmd('iperf -s')

    clients = [net.getNodeByName('h%d' % (i+1)) for i in xrange(1, args.n)]
    waitListening(clients[0], h1, 5001)

    monitors = []

    monitor = multiprocessing.Process(target=monitor_cpu, args=('%s/cpu.txt' % args.dir,))
    monitor.start()
    monitors.append(monitor)

    monitor = multiprocessing.Process(target=monitor_qlen, args=('s1-eth1', 0.01, '%s/qlen_s1-eth1.txt' % (args.dir)))
    monitor.start()
    monitors.append(monitor)

    monitor = multiprocessing.Process(target=monitor_devs_ng, args=('%s/txrate.txt' % args.dir, 0.01))
    monitor.start()
    monitors.append(monitor)
    Popen("rmmod tcp_probe; modprobe tcp_probe; cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)
    #CLI(net)

    for i in xrange(1, args.n):
        node_name = 'h%d' % (i+1)
        if args.udp:
            cmd = 'iperf -c 10.0.0.1 -t %d -i 1 -u -b %sM > %s/iperf_%s.txt' % (seconds, args.bw, args.dir, node_name)
        else:
            cmd = 'iperf -c 10.0.0.1 -t %d -i 1 -Z reno > %s/iperf_%s.txt' % (seconds, args.dir, node_name)
        h = net.getNodeByName(node_name)
        h.sendCmd(cmd)

    net.getNodeByName('h2').popen('/bin/ping 10.0.0.1 > %s/ping.txt' % args.dir,
	    shell=True)
    if args.tcpdump:
	for i in xrange(args.n):
	    node_name = 'h%d' % (i+1)
	    net.getNodeByName(node_name).popen('tcpdump -ni %s-eth0 -s0 -w \
		    %s/%s_tcpdump.pcap' % (node_name, args.dir, node_name), 
		    shell=True)
    progress(seconds)
    for monitor in monitors:
        monitor.terminate()

    net.getNodeByName('h1').pexec("/bin/netstat -s > %s/netstat.txt" %
	    args.dir, shell=True)
    net.getNodeByName('h1').pexec("/sbin/ifconfig > %s/ifconfig.txt" %
	    args.dir, shell=True)
    net.getNodeByName('h1').pexec("/sbin/tc -s qdisc > %s/tc-stats.txt" %
    	    args.dir, shell=True)
    net.stop()
    disable_dctcp()
    disable_tcp_ecn()
    Popen("killall -9 cat ping top bwm-ng", shell=True).wait()

if __name__ == '__main__':
    main()
