#!/usr/bin/python

import fileinput
from json import loads
from optparse import OptionParser
from sys import exit, path
from operator import and_, add
import os
import re
import math

path.append( '..' )

import lib.plot_defaults
import matplotlib.pyplot as plt

from cpuiso.CPUIsolationLib import intListCallback
from lib.plot import colorGenerator
from lib.helper import avg, stdev

def sched_for(indir):
    if 'cfs' in indir:
	return 'bwc'
    if 'none' in indir:
   	return 'default'
    for sched in 'rt', 'cfs', 'none':
        if sched in indir:
            return sched
    return indir

def plot_pingpong(plotopts):
    fig = plt.figure( 1 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    # plt.title('Latency test (UDP ping)')
    plt.ylabel( 'Round-trip latency (ms)' )
    plt.xlabel( 'No. of hosts' )
    cgen = colorGenerator()
    if plotopts.box:
        for indir in plotopts.args:
            x, y = [], []
            widths = []
            for n in plotopts.counts:
                infile = '%s/u-%d' % (indir, n)
                ping_stats = parsePing(infile)
                x.append(n)
                y.append(ping_stats)
                widths.append(math.log(n,2))
            plt.boxplot(y, positions=x, widths=widths)
        # plt.xscale('log')
        plt.grid( True )
        # plt.ylim(ymin=0.0, ymax=0.1)
    else:
        for indir in plotopts.args:
            x, y, yerr, ymin, ymax, ysd = [], [], [], [], [], []
            widths = []
            for n in plotopts.counts:
                infile = '%s/u-%d' % (indir, n)
                ping_stats = parsePing(infile)
                x.append(n)
                y.append(avg(ping_stats))
                sd = 2*stdev(ping_stats)
                yerr.append(2*sd)
                ymin.append(min(ping_stats))
                ymax.append(max(ping_stats))
                ysd.append(sd)
            color = cgen.next()
            label = sched_for(indir)
            plt.errorbar(x, y, yerr=yerr, color=color, label=label, linewidth=2)
            # plt.plot(x, ymax, ':', color=color)
        #plt.xscale('log')
        plt.yscale('log')
        plt.grid( True )
    plt.legend(loc=0)
    plt.ylim(ymin=0)
    plt.xlim(xmax=max(x) + 10)
    savePlot(plotopts, 'pingpong')

def parsePing(infile):
    ping_stats = []
    f = open(infile, 'r')
    for line in f.readlines():
        line = line.strip()
        if line:
            time = float(line) * 1000.0
            ping_stats.append(time)
    f.close()
    # print ping_stats
    return ping_stats
        
def readData( files ):
    "Read input data from pair_intervals run"
    results = []
    for line in fileinput.input( files ):
        if line[ 0 ] == '#':
            continue
        data = loads( line )
        if type( data ) == dict:
            opts = loads(line)
        elif type( data ) == list:
            results.append(data)
    return results, opts

def savePlot(opts, plot_name):
    if(opts.dir == ''):
        plt.show()
        return
    file_prefix = os.path.splitext(os.path.basename(opts.args[0]))[0] if opts.prefix == '' else opts.prefix
    fname = '%s/%s-%s.pdf' % (opts.dir, file_prefix, plot_name)
    print 'Saving plot to %s' % fname
    plt.savefig(fname)

def parseOptions():
    "Parse command line options"
    parser = OptionParser( 'usage: %prog [options] [input files]' )
    parser.add_option( '-d', '--dir', dest='dir',
                      type='string', default='', 
                      help='save plots in the directory "dir"' )
    parser.add_option( '-p', '--prefix', dest='prefix',
                      type='string', default='', 
                      help='custom prefix for saved figures' )
    parser.add_option( '-c', '--counts', dest='counts',
        action='callback', callback=intListCallback, default=[ 2 ],
        type='string', help='specify node counts, e.g. 10,20,40' )
    parser.add_option( '-b', '--box', dest='box',
                      default=False, action='store_true',
                      help='plot box plots' )
    ( options, args ) = parser.parse_args()
    return options, args

if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args
    plot_pingpong(plotopts)
