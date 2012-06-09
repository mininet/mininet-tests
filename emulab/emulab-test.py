#!/usr/bin/python

"""
Simple test of mininet vs. emulab
"""

from mininet.net import Mininet
from mininet.node import Host
from mininet.topo import SingleSwitchTopo, Edge
from mininet.log import setLogLevel
from mininet.topo import Topo, Node, Edge
from mininet.util import quietRun, numCores
from sys import exit

class EmulabTopo( Topo ):
    "Reproduce emulab topology so script will work."
    
    def __init__( self, enable_all=True, testbw=100, 
                  lanbw=10, reduce=0, cpu=None ):
        "Create custom topo."
        
        # Add default members to class.
        super( EmulabTopo, self ).__init__()

        # hosts
        hosts = [ 'node-'+c for c in 'ABCDEFGHIJ' ]
        for host in hosts:
            self.add_node( host, Node( is_switch=False, cpu=cpu ) )
        
        # switches
        testsw, lansw = 'testsw', 'lansw'
        self.add_node( testsw, Node( is_switch=True ) )
        self.add_node( lansw, Node( is_switch=True ) )

        # Add edges
        for host in hosts:
            self.add_edge( host, lansw, Edge( bw=lanbw ) )
        bw1 = testbw - reduce if reduce > 0 else testbw
        self.add_edge( hosts[0], testsw, Edge( bw=bw1 ) )
        self.add_edge( hosts[1], testsw, Edge( bw=testbw ) )        
        # Consider all switches and hosts 'on'
        self.enable_all()

def custom(Class, **custom):
    "Customized object factory"
    def factory(*args, **kwargs):
        kwargs.update( custom )
        return Class(*args, **kwargs)
    return factory


def run( sched='cfs', cpu=.05, fastbw=100, lanbw=10, reduce=0):
    "Run test"
    quietRun( 'pkill -9 iperf')
    topo = EmulabTopo( testbw=fastbw, lanbw=lanbw, cpu=cpu)
    net = Mininet(topo, 
                  host=custom( Host, sched=sched, period_us=10000,
                               isIsolated=(sched is not 'none') ) )
    net.start()
    # Set up routes for extra link
    print [ h.name for h in net.hosts]
    nodea, nodeb = net.nameToNode['node-A'], net.nameToNode['node-B']
    nodea.cmdPrint( 'ifconfig ' + nodea.intfs[1] + ' up')
    nodeb.cmdPrint( 'ifconfig ' + nodeb.intfs[1] + ' up')
    nodea.setIP(nodea.intfs[1], '10.0.0.11')
    nodeb.setIP(nodeb.intfs[1], '10.0.0.12')
    nodea.cmdPrint('route add -host 10.0.0.12 dev ' + nodea.intfs[1] )
    nodeb.cmdPrint('route add -host 10.0.0.11 dev ' + nodeb.intfs[1] )
    nodea.cmdPrint('route del -net 10.0.0.0/8' )
    nodeb.cmdPrint('route del -net 10.0.0.0/8' )
    nodea.cmdPrint('route -n')
    nodeb.cmdPrint('route -n')
    print "*** starting sshd servers"
    for host in net.hosts:
        host.name, host.IP()
        host.cmdPrint('/usr/sbin/sshd')
    print "*** checking ping and ssh connectivity"
    net.pingAll()
    print "*** fixing local route on nodea"
    nodea.cmdPrint("ifconfig lo up")
    nodea.cmdPrint("ping -c1 " + nodea.IP() )
    for suffix in 'ABCDEFGHIJ':
        nodea.cmdPrint( 'ssh node-' + suffix + ' hostname')
    print "*** running test"
    host = quietRun('hostname').strip()
    cores = numCores()
    outfile = "emulab-%s-%sp-%s-%s-%s.out" % ( host, cores, sched, cpu, fastbw)
    nodea.cmdPrint("./emulab-test.sh  2>&1 | tee %s; echo done" % outfile)
    print "stopping sshd servers"
    for host in net.hosts:
        host.cmdPrint('pkill -9 -f /usr/sbin/sshd')
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    targetbw=200
    targetcpu=.09
    run( sched='cfs', cpu=targetcpu, fastbw=targetbw )
    run( sched='cfs', cpu=targetcpu, fastbw=None )
    run( sched='none', cpu=None, fastbw=targetbw )
    run( sched='none', cpu=None, fastbw=None, lanbw=None )




