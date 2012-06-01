#!/usr/bin/python

"CS244 Assignment 1: Parking Lot"

import sys
sys.path = ['../'] + sys.path

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from multiprocessing import Process
from subprocess import Popen
import termcolor as T
import argparse

import os
from util.monitor import monitor_cpu, monitor_qlen, monitor_devs_ng


def cprint(s, color, cr=True):
    """Print in color
       s: string to print
       color: color to use"""
    if cr:
        print T.colored(s, color)
    else:
        print T.colored(s, color),

parser = argparse.ArgumentParser(description="Parking lot tests")
parser.add_argument('--bw', '-b',
                    type=float,
                    help="Bandwidth of network links",
                    required=True)

parser.add_argument('--dir', '-d',
                    help="Directory to store outputs",
                    default="results")

parser.add_argument('-n',
                    type=int,
                    help=("Number of senders in the parking lot topo."
                          "Must be >= 1"),
                    required=True)

parser.add_argument('--cli', '-c',
                    action='store_true',
                    help='Run CLI for topology debugging purposes')

parser.add_argument('--time', '-t',
                    dest="time",
                    type=int,
                    help="Duration of the experiment.",
                    default=60)

# Expt parameters
args = parser.parse_args()

if not os.path.exists(args.dir):
    os.makedirs(args.dir)

lg.setLogLevel('info')


# Topology to be instantiated in Mininet
class ParkingLotTopo(Topo):
    "Parking Lot Topology"

    def __init__(self, n=1, cpu=.1, bw=10, delay=None,
                 max_queue_size=None, **params):
        """Parking lot topology with one receiver
           and n clients.
           n: number of clients
           cpu: system fraction for each host
           bw: link bandwidth in Mb/s
           delay: link delay (e.g. 10ms)"""

        # BL: This is intentionally a bit pedantic, for
        # illustrative purposes!!

        # Initialize topo
        Topo.__init__(self, **params)

        # Host and link configuration
        hconfig = {'cpu': cpu}
        lconfig = {'bw': bw, 'delay': delay,
                   'max_queue_size': max_queue_size }

        # Create N switches, N clients, and 1 receiver
        switches = [self.add_switch('s%s' % s,)
                     for s in irange(1, n)]

        clients = [self.add_host('h%s' % c, **hconfig)
                   for c in irange(1, n)]

        receiver = self.add_host('receiver')

        # Switch ports 1:uplink 2:hostlink 3:downlink
        uplink, hostlink, downlink = 1, 2, 3

        # Wire up switches
        for s1, s2 in zip(switches[:-1], switches[1:]):
            self.add_link(s1, s2,
                          port1=downlink, port2=uplink, **lconfig)

        # Wire up receiver
        self.add_link(receiver, switches[0],
                      port1=0, port2=uplink, **lconfig)

        # Wire up clients:
        for client, switch in zip(clients, switches):
            self.add_link(client, switch,
                          port1=0, port2=hostlink, **lconfig)


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
    "Report progress of time"
    while t > 0:
        cprint('  %3d seconds left  \r' % (t), 'cyan', cr=False)
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print


def start_tcpprobe():
    os.system("rmmod tcp_probe &>/dev/null; modprobe tcp_probe;")
    Popen("cat /proc/net/tcpprobe > %s/tcp_probe.txt" % args.dir, shell=True)

def stop_tcpprobe():
    os.system("killall -9 cat; rmmod tcp_probe &>/dev/null;")

def run_parkinglot_expt(net, n):
    "Run experiment"

    seconds = args.time

    # Start the bandwidth and cwnd monitors in the background
    monitors = []

    monitor = Process(target=monitor_devs_ng,
                      args=('%s/bwm.txt' % args.dir, 1.0))
    monitor.start()
    monitors.append(monitor)

    monitor = Process(target=monitor_cpu, args=('%s/cpu.txt' % args.dir,))
    monitor.start()
    monitors.append(monitor)

    monitor = Process(target=monitor_qlen, args=('s1-eth1', 0.01, '%s/qlen_s1-eth1.txt' % (args.dir)))
    monitor.start()
    monitors.append(monitor)

    start_tcpprobe()

    # Get receiver and clients
    recvr = net.getNodeByName('receiver')
    clients = [net.getNodeByName('h%s' % i)
                for i in irange(1, n)]
    cprint("Receiver: %s" % recvr, 'magenta')
    cprint("Clients: " + ', '.join([str(c) for c in clients]),
           'magenta')

    # Start the receiver
    port = 5001
    recvr.cmd('iperf -s -p', port,
              '> %s/iperf_server.txt' % args.dir, '&')

    waitListening(clients[0], recvr, port)

    # Start the client iperfs
    cmd = ['iperf',
           '-c', recvr.IP(),
           '-p', port,
           '-t', seconds,
           '-i', 1,  # reporting interval
           '-Z reno',  # use TCP Reno
           '-yc']   # report output as comma-separated values
    outfile = {}
    for c in clients:
        outfile[c] = '%s/iperf_%s.txt' % (args.dir, c.name)
        # Ugh, this is a bit ugly....
        redirect = ['>', outfile[c]]
        c.sendCmd(cmd + redirect, printPid=False)

    # Count down time
    progress(seconds)

    # Wait for clients to complete
    # If you don't do this, iperfs may keep running!
    output('Waiting for clients to complete...\n')
    for c in clients:
        c.waitOutput(verbose=True)

    recvr.cmd('kill %iperf')

    # Shut down monitors
    for monitor in monitors:
	monitor.terminate()
    stop_tcpprobe()

def check_prereqs():
    "Check for necessary programs"
    prereqs = ['telnet', 'bwm-ng', 'iperf', 'ping']
    for p in prereqs:
        if not quietRun('which ' + p):
            raise Exception((
                'Could not find %s - make sure that it is '
                'installed and in your $PATH') % p)


def main():
    "Create and run experiment"
    start = time()

    topo = ParkingLotTopo(n=args.n)

    host = custom(CPULimitedHost, cpu=.15)  # 15% of system bandwidth
    link = custom(TCLink, bw=args.bw, delay='1ms',
                  max_queue_size=200)

    net = Mininet(topo=topo, host=host, link=link)

    net.start()

    cprint("*** Dumping network connections:", "green")
    dumpNetConnections(net)

    cprint("*** Testing connectivity", "blue")

    net.pingAll()

    if args.cli:
        # Run CLI instead of experiment
        CLI(net)
    else:
        cprint("*** Running experiment", "magenta")
        run_parkinglot_expt(net, n=args.n)

    net.stop()
    end = time()
    os.system("killall -9 bwm-ng")
    cprint("Experiment took %.3f seconds" % (end - start), "yellow")

if __name__ == '__main__':
    check_prereqs()
    main()
