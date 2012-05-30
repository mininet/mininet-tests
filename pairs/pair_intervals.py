#!/usr/bin/python

"""
pair_intervals.py: test bandwidth through a single pair of hosts,
connected either via a switch or raw links, over time.

Bob Lantz
"""

import re
from time import sleep, time
from sys import exit, stdout, stderr
from optparse import OptionParser
from json import dumps

from mininet.net import Mininet
from mininet.node import Controller, CPULimitedHost
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info, warn, output

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Host
from mininet.util import quietRun, natural, custom

from decimal import Decimal

# Simple topologies: sets of host pairs

class PairTopo( Topo ):
    "A set of host pairs connected by single links"
    
    def __init__( self, pairs, useSwitches ):
        super( PairTopo, self ).__init__()
        for h in range( 1, pairs + 1 ):
            if useSwitches:
                self.addSwitchPair( h, pairs + h, pairs + pairs + h )
            else:
                self.addPair( h, pairs + h )
    
    def addPair( self, h1, h2 ):
        "Add a pair of linked hosts, h1 <-> h2"
        h1, h2 = 'h%d' % h1, 'h%d' % h2
        self.add_host( h1 )
        self.add_host( h2 )
        self.add_link( h1, h2 )
    
    def addSwitchPair( self, h1, h2, s1 ):
        "Add a pair of linked hosts, h1 <-> s1 <-> h2"
        h1, h2, s1  = 'h%d' % h1, 'h%d' % h2, 's%d' % s1        
        self.add_node( h1 )
        self.add_host( h2 )
        self.add_switch( s1 )
        self.add_link( h1, s1 )
        self.add_link( h2, s1 )

def pairNet( pairs=1, useSwitches=False, bw=None, cpu=-1, **kwargs ):
    "Convenience function for creating pair networks"
    clients, servers = [], []
    # This is a bit ugly - a lot of work to avoid flushing
    # routes; I think we should rethink how that works.
    class MyHost( CPULimitedHost ):
        "Put clients in root namespace and DON'T flush routes"
        def __init__( self, name, **kwargs ):
            # First N (=pairs) hosts are clients, in root NS
            kwargs.pop('inNamespace', True)
            isServer = int( name[ 1: ] ) > pairs
            CPULimitedHost.__init__( self, name, inNamespace=isServer, **kwargs )
        def setDefaultRoute( self, intf ):
            "Hack of sorts: don't set or flush route"
            pass

    cpu = custom( MyHost, cpu=cpu )
    link = custom( TCLink, bw=bw )
    topo = PairTopo( pairs, useSwitches )
    net = Mininet( topo, host=MyHost, **kwargs )
    net.hosts = sorted( net.hosts, key=lambda h: natural( h.name ) )
    clients, servers = net.hosts[ :pairs ], net.hosts[ pairs: ]
    info( "*** Configuring host routes\n" )
    for client, server in zip( clients, servers ):
        client.setHostRoute( server.IP(), client.defaultIntf() )
        server.setHostRoute( client.IP(), server.defaultIntf() )
    return net, clients, servers

# Utility functions

def dictFromList( items ):
    "Return dict[1..N] from list of items"
    return dict( zip( range( 1, len( items ) + 1 ), items ) )

def listening( src, dest, port=5001 ):
    "Return True if we can connect from src to dest on port"
    cmd = 'echo A | telnet -e A %s %s' % (dest.IP(), port)
    result = src.cmd( cmd )
    return 'Connected' in result

def pct( x ):
    "pretty percent"
    return round(  x * 100.0, 2 )

# Parse output from packetcount.c

def parseIntfStats( startTime, stats ):
    """Parse stats; return dict[intf] of (s, rxbytes, txbytes)
       and list of ( start, stop, user%... )"""
    spaces = re.compile('\s+')
    colons = re.compile( r'\:' )
    seconds = re.compile( r'(\d+\.\d+) seconds')
    intfEntries, cpuEntries, lastEntries = {}, [], []
    for line in stats.split( '\n' ):
        m = seconds.search(line)
        if m:
            s = round( float( m.group( 1 ) ) - startTime, 3 )
        elif '-eth' in line:
            line = spaces.sub( ' ', line ).split()
            intf = colons.sub( '', line[ 0 ] )
            rxbytes, txbytes = int( line[ 1 ] ), int( line[ 9 ] )
            intfEntries[ intf ] = intfEntries.get( intf, [] ) +  [
                    (s, rxbytes, txbytes ) ]
        elif 'cpu ' in line:
            line = spaces.sub( ' ', line ).split()
            entries = map( float, line[ 1 : ] )
            if lastEntries:
                dtotal = sum( entries ) - sum( lastEntries )
                if dtotal == 0:
                    raise Exception( "CPU was stalled from %s to %s - giving up" %
                                     ( lastTime, s ) )
                deltaPct = [ pct( ( x1 - x0 ) / dtotal ) 
                             for x1, x0 in zip( entries, lastEntries) ]
                interval = s - lastTime
                cpuEntries += [ [ lastTime, s ] + deltaPct ]
            lastTime = s
            lastEntries = entries

    return intfEntries, cpuEntries

def remoteIntf( intf ):
    "Return other side of link that intf is connected to"
    link = intf.link
    return link.intf1 if intf == link.intf2 else link.intf2

# Iperf pair test

def iperfPairs( opts, clients, servers ):
    "Run iperf semi-simultaneously one way for all pairs"
    pairs = len( clients )
    plist = zip( clients, servers )
    info( '*** Clients: %s\n' %  ' '.join( [ c.name for c in clients ] ) )
    info( '*** Servers: %s\n' %  ' '.join( [ c.name for c in servers ] ) )
    info( "*** Shutting down old iperfs\n")
    quietRun( "pkill -9 iperf" )
    info( "*** Starting iperf servers\n" )
    for dest in servers:
        dest.cmd( "iperf -s &" )
    info( "*** Waiting for servers to start listening\n" )
    for src, dest in plist:
        info( dest.name, '' )
        while not listening( src, dest ):
            info( '.' )
            sleep( .5 )
    info( '\n' )
    info( "*** Starting iperf clients\n" )
    for src, dest in plist:
        src.sendCmd( "sleep 1; iperf -t %s -i .5 -c %s" % (
            opts.time, dest.IP() ) )
    info( '*** Running cpu and packet count monitor\n' )
    startTime = int( time() )
    cmd = "./packetcount %s .5" % ( opts.time + 2 )
    stats = quietRun( cmd  )
    intfEntries, cpuEntries = parseIntfStats( startTime, stats )
    info( "*** Waiting for clients to complete\n" )
    results = []
    for src, dest in plist:
        result = src.waitOutput()
        dest.cmd( "kill -9 %iperf" )
        # Wait for iperf server to terminate
        dest.cmd( "wait" )
        # We look at the stats for the remote side of the destination's
        # default intf, as it is 1) now in the root namespace and easy to
        # read and 2) guaranteed by the veth implementation to have
        # the same byte stats as the local side (with rx and tx reversed,
        # naturally.)  Otherwise
        # we would have to spawn a packetcount process on each server
        intfName = remoteIntf( dest.defaultIntf() ).name
        intervals = intfEntries[ intfName ]
        # Note: we are reversing txbytes and rxbytes to reflect
        # the statistics *at the destination*
        results += [ { 'src': src.name, 'dest': dest.name,
                    'destStats(s,txbytes,rxbytes)': intervals } ]
    return results, cpuEntries

def pairTest( opts ):
    """Run a set of tests for a series of counts, returning
        accumulated iperf bandwidth per interval for each test."""
    results = []
    initOutput( opts.outfile )
    # 9 categories in linux 2.6+
    cpuHeader = ( 'cpu(start,stop,user%,nice%,sys%,idle%,iowait%,'
                 'irq%,sirq%,steal%,guest%)' )
    for pairs in opts.counts:
        cpu = 4./pairs if opts.cpu else -1
        bw = opts.bw if (opts.bw > 0) else None
        net, clients, servers = pairNet( 
            pairs=pairs, useSwitches=opts.switches, cpu=cpu, bw=bw)
        net.start()
        hosts = dictFromList( net.hosts )
        intervals, cpuEntries = iperfPairs( opts, clients, servers )
        net.stop()
        # Write output incrementally in case of failure
        result = { 'pairs': pairs, 'results': intervals,
            cpuHeader: cpuEntries }
        appendOutput( opts, [ result ] )
        results += [ result ]
    return results

# Floating point madness; thanks stackoverflow

class PrettyFloats( float ):
    def __repr__( self ):
        return '%.15g' % self

def prettyFloats( obj):
    "Beautify floats in dict/list/tuple data structure"
    if isinstance( obj, float ):
        return PrettyFloats( obj )
    elif isinstance( obj, dict ):
        return dict((k, prettyFloats(v)) for k, v in obj.items())
    elif isinstance( obj, ( list, tuple ) ):
        return map( prettyFloats, obj )
    return obj

# Incrementally create and append to output file

def initOutput( name ):
    "Initialize an output file"
    f =  open( name, 'w') if name else stdout
    print >>f, '# pair_intervals results'
    print >>f, dumps( opts.__dict__ )
    if name:
        f.close()

def appendOutput( opts, totals ):
    "Append results as JSON to stdout or opts.outfile"
    info( '*** Dumping result\n' )
    f = open( opts.outfile, 'a' ) if opts.outfile else stdout
    print >>f, dumps( prettyFloats( totals ) )
    if opts.outfile:
        f.close()

# Command line options and sanity check

def intListCallback( option, opt, value, parser ):
    "Callback for parseOptions"
    value = [ int( x ) for x in value.split( ',' ) ]
    setattr( parser.values, option.dest, value )

def parseOptions():
    "Parse command line options"
    parser = OptionParser()
    parser.add_option( '-o', '--output', dest='outfile',
                      default=None, help='write output to file' )
    parser.add_option( '-t', '--time', dest='time',
                      type='int', default=10, help='select iperf time interval' )
    parser.add_option( '-c', '--counts', dest='counts',
                      action='callback', callback=intListCallback, default=[ 1 ],
                      type='string',
                      help='specify pair counts, e.g. 10,20,40' )
    parser.add_option( '-s', '--switches', dest='switches',
                      action='store_true', default=False,
                      help='connect hosts with switches rather than bare links' )
    parser.add_option( '-b', '--bw', dest='bw', type='int',
                      default=0, help='use bandwidth limiting' )
    parser.add_option( '-p', '--cpu', dest='cpu', 
                      action='store_true', default=False, 
                      help='use cpu isolation' )
    options, args = parser.parse_args()
    return options, args

def sanityCheck():
    "Make sure we have stuff we need"
    reqs = [ 'iperf', 'telnet', './packetcount' ]
    for req in reqs:
        if quietRun( 'which ' + req ) == '':
            print ( "Error: cannot find", req,
               " - make sure it is built and/or installed." )
            exit( 1 )

if __name__ == '__main__':
    setLogLevel( 'info' )
    opts, args = parseOptions()
    sanityCheck()
    pairTest( opts )
