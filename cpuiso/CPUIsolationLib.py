#!/usr/bin/python

"""
Tests for CPU isolation.
"""

import os
import re
import sys
from sys import exit, stdout, stderr
flush = sys.stdout.flush
from time import sleep
from sys import exit, stdout, stderr
from json import dumps

from mininet.node import CPULimitedHost
from mininet.topo import Topo
from mininet.util import quietRun, numCores, natural
from mininet.log import lg, setLogLevel, info, warn, output

CPUDIR = '../cpuiso/cpu'

class CPUIsolationHost( CPULimitedHost ):
    "Degenerate host with no interfaces"
    def setIP( self, *args, **kwargs ):
        "Ignore attempts to set an IP address"
        pass

class CPUIsolationTopo( Topo ):
    "Topology for a set of disconnected hosts"
    def __init__( self, N ):
        Topo.__init__( self )
        for i in range( 1, N+1 ):
            self.add_host( 'h%s' % i )

def get_cpu_pid(s):
    out, err, code  = s.pexec( 'ps aux' )
    lines = out.split('\n')
    for l in lines:
        if re.search('cpu-stress', l) is not None:
            if len(l) > 2:
                return int(l.split()[1])
    return None

def start_monitor_cpu(s, fname):
    bash = quietRun('which bash').strip()
    pid = None
    print 'Getting PID of the cpu-stress process in host %s' % s.name
    while pid is None:
        print '.',
        pid = get_cpu_pid(s)
        sleep(0.5)
    print 'pid: %d' % pid
    quietRun('rm -rf %s' % fname)
    cpu_stress_cmd = ('%s -c "(top -b -p %d -d 1 | grep --line-buffered cpu-stress) > %s" &' % 
                      (bash, pid, fname))
    print cpu_stress_cmd
    return s.cmd(cpu_stress_cmd)

def stop_monitor_cpu(s):
    s.cmd('killall -9 top')

def parse_cpu_log(fname):
    f = open(fname, 'r')
    ret = {'xvals':[], 'cpuvals':[]}
    cur_time, cur_cpu = 0, None
    for l in f:
        vals = l.split()
        if len(vals) < 12:
            continue
        if re.search('cpu-stress', l) is not None:
            cur_cpu = float(vals[8])
            ret['xvals'].append(cur_time)
            ret['cpuvals'].append(cur_cpu)
            cur_time += 1
    #ignore the first value -- it's usually a bad value
    ret['xvals'].pop()
    ret['cpuvals'].pop(0)
    return ret

def diff_list(L):
    return [y - x for x,y in zip(L,L[1:])]

def double_diff_list(L):
    return [[y - x for x, y in zip(a, b)] for a, b in zip(L, L[1:])]

def parse_cpuacct(stats, cpulimit=None):
    '''Return the following:
        cpu_usage[n], with each element a dict{'xvals':[], 'cpuvals':[]}
        cpu_stat[n] with each element a dict{'xvals':[], 'uservals': [], 'systemvals': []}
        '''
    cpu_usage = {}

    rec_re = re.compile(r'cgroup (\S+),time (\d+.\d+)')
    spaces = re.compile('\s+')

    host = None
    time = None

    # Report CPU limit in CPU seconds rather than as a fraction (!)
    cores = numCores()
    cpulimit *= cores

    for line in stats.split('\n'):
        m = rec_re.match(line)
        if m:
            host = m.group(1)
            time = float(m.group(2))
        else:
            line = spaces.sub( ' ', line ).split()
            if 'usage' in line:
                cpuval = float(line[1])
                if host is None or time is None:
                    continue
                if host not in cpu_usage:
                    cpu_usage[host] = {'xvals':[], 'cpuvals':[], 'uservals':[],
                     'systemvals':[], 'percpuvals':[], 'cpulimit': cpulimit }
                cpu_usage[host]['xvals'].append(time)
                cpu_usage[host]['cpuvals'].append(cpuval)

            elif 'user' in line:
                userval = float(line[1])
                if host is None or time is None:
                    continue
                cpu_usage[host]['uservals'].append(userval)

            elif 'system' in line:
                systemval = float(line[1])
                if host is None or time is None:
                    continue
                cpu_usage[host]['systemvals'].append(systemval)
            elif 'percpu' in line:
                percpuval = map(float, line[1:])
                if host is None or time is None:
                    continue
                cpu_usage[host]['percpuvals'].append(percpuval)

    # Round results to reported (though not necessarily actual) accuracy (ns, HZ)
    def r9(x):
        return round(x,9)
    def r2(x):
        return round(x,2)

    for k,v in cpu_usage.iteritems():
        intervals = diff_list(v['xvals'])
        v['xvals'] = [r9(x - v['xvals'][0]) for x in v['xvals']]
        v['xvals'].pop(0)
        v['cpuvals'] = [r9(1e-9*x/y) for x, y in zip(diff_list(v['cpuvals']), intervals)]
        v['uservals'] = [r2(1e-2*x/y) for x, y in zip(diff_list(v['uservals']), intervals)]
        v['systemvals'] = [r2(1e-2*x/y) for x, y in zip(diff_list(v['systemvals']), intervals)]
        v['percpuvals'] = [[r9(1e-9*x/y) for x in l] 
                           for l, y in zip(double_diff_list(v['percpuvals']), intervals)]
        v['cpucount'] = cores

    return [cpu_usage[k] for k in sorted(cpu_usage.keys(), key=natural)]


# Floating point madness; thanks stackoverflow

class PrettyFloats( float ):
    def __repr__( self ):
        return '%.15g' % self

def prettyFloats( obj):
    if isinstance( obj, float ):
        return PrettyFloats( obj )
    elif isinstance( obj, dict ):
        return dict((k, prettyFloats(v)) for k, v in obj.items())
    elif isinstance( obj, ( list, tuple ) ):
        return map( prettyFloats, obj )             
    return obj
   
def initOutput( name, opts ):
    "Initialize an output file"
    if name:
        dirname = os.path.dirname(name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        f = open( name, 'w')
    else:
        f = stdout
    print >>f, '# CPU Isolation results - times are in seconds'
    print >>f, dumps( opts.__dict__ )
    if name:
        f.close()

def appendOutput( outfile, totals ):
    "Append results as JSON to stdout or opts.outfile"
    info( '*** Dumping result\n' )
    f = open( outfile, 'a' ) if outfile else stdout
    print >>f, dumps( prettyFloats( totals ) )
    if outfile:
        f.close()


def checkForExec( prog,dirname ):
    """Check for executable prog; if not found,
       prompt to compile src in dirname"""
    prog = dirname + '/' + prog
    if quietRun( 'which ' +  prog ) == '':
        print ( "Error: cannot find %s - make sure %s.c" 
                " is compiled (cd %s; make) " % ( 
                prog, prog, dirname ) )
        sys.exit( 1 )
    return prog

def cpuStressName():
    "Return name of cpu-stress program"
    return checkForExec( 'cpu-stress', CPUDIR )

def timerName():
    "Return name of timer program"
    return checkForExec( 'timer', CPUDIR )

def cpuMonitorName():
    "Return name of CPU monitor program"
    return checkForExec( 'cpumonitor', CPUDIR )


def sanityCheck():
    "Make sure we have stuff we need"
    return ( cpuStressName(), timerName(),
             cpuMonitorName() )

# Options helper functions.

def intListCallback( option, opt, value, parser ):
    "Callback for parseOptions"
    value = [ int( x ) for x in value.split( ',' ) ]
    setattr( parser.values, option.dest, value )

def floatListCallback( option, opt, value, parser ):
    "Callback for parseOptions"
    value = [ float( x ) for x in value.split( ',' ) ]
    setattr( parser.values, option.dest, value )
