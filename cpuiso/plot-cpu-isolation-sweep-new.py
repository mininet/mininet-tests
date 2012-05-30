#!/usr/bin/python
"""
Accumulate results and calculate variance
"""

import plot_defaults

import fileinput
from math import sqrt
from json import loads, dumps
from optparse import OptionParser
from sys import exit
from operator import and_, add
import os
import re

# We use python-matplotlib and numpy for graphing
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from CPUIsolationLib import intListCallback

FONTSIZE = 12 

def sigma2( nums ):
    "Calculate variance (sigma^2) for a list of numbers"
    n = len( nums )
    total = sum( nums )
    mean = total / n
    sumsq = sum( [ (x - mean) * (x - mean) for x in nums ] )
    variance = sumsq / n
    return variance

def sigma( nums ):
    "Calculate standard deviation for list of numbers"
    return sqrt( sigma2 ( nums ) )

def coeff_var(nums):
    mean = sum(nums) / len(nums)
    return sigma(nums) / mean

def accumulateLinkBw( results ):
    "Accumulate overall link bandwidth, reported by iperf"
    bws = [ bps for src, dest, result, bps in results ]
    totalbw = sum( bws )
    stdev = None  # was: sigma( bws )
    return totalbw, stdev

def rmse( nums, expected ):
    "Calculate sqrt( sum( (x[i] - expected)^2 ) / n ) "
    n = len( nums )
    sumsq = sum( [ (x - expected) * (x - expected) for x in nums ] )
    mse = sumsq / n
    result = sqrt( mse )
    return result
    

"""
Plot madness.....

This is currently extremely opaque and hard to understand and modify.

Conceptually we have:

- varying numbers of hosts
- varying target utilizations
- measurements over time for each host
- potentially multiple runs

So, we sort them into the following:

(hosts, util, x values, [y values])

And then plot them.

But guess what??!?!?! The results already have this included!!!
This should really be quite easy to plot!!!

Note that the specific y values can vary. In some cases (time plot), we
simply want to plot all of the y values.

In other cases, we want to merge the list of y values into a single
list (e.g. average or standard deviation across hosts.)

more junk to think about:
- for each set of results, host count is number of results
- each result includes cpulimit for that result as well as (real) cpu count
- so, we can derive all the info we need simply by looking at the results
- however, they should match the options at the top of the file


"""


def plotIntervals( plotopts, results ):
    "Plot CPU utilization over time "
    fig = plt.figure( 2 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    defaults = { 'color': 'black' }  # was: { 'linewidth': 2 }
    totals = {}

    ax = fig.add_subplot( 111 )

    lines = {}

    for opts, runs in results:
        for run in runs:
            hosts = len(run)
            for r in run:
                cpucount = r['cpucount']
                cpulimit = float(r['cpulimit'])  # cpu seconds per second
                
                # Expected utilization is divided evenly over hosts
                exp_value = cpulimit

                xvals = r['xvals']
                yvals = [ float(v) for v in r['cpuvals']]

                if plotopts.norm:
                    yvals = [float(y) / exp_value for y in yvals]
                else:
                    plt.axhline( y=exp_value, linestyle='--', color='black', 
                                    linewidth=2 )

                lines[hosts] = lines.get(hosts, []) + [(cpulimit, cpucount, xvals, yvals)]

    colors = {}
    cgen = colorGenerator()
        
    print lines.keys()
    
    sched = opts['sched']
    static = 'static' if opts['static'] else 'dyn'
    for hosts in opts['counts']:
        # Reverse order so that highest utils are at the top
        data = reversed(lines[hosts])
        for cpulimit, cpucount, xvals, yvals in data:
            util = cpulimit * hosts / cpucount * 100.0
            label = "%sp*%.0f%%/%sh-%s-%s" % (cpucount, util, hosts, sched, static )
            color, label = linkLegend( cgen, colors, label )
            ax.plot(xvals, yvals, '-', color=color, label=label, linewidth=1 )

    if plotopts.norm:
        plt.title('CPU utilization (normalized to expected)')
	plt.ylabel('CPU utilization (normalized expected)')
    else:
        plt.title('CPU utilization')
    	plt.ylabel( 'CPU seconds/second')
    plt.xlabel( 'time (s)' )

    label = 'cpu isolation'

    plt.grid()

    if not plotopts.nolegend:
        plt.legend()
        
    savePlot(plotopts, 'time')

def oldtable( plotopts, results ):
    "Print table of sample mean, min and max"
    
    format = "%-5s %-7s %-4s %-6s %-6s  %-6s  %-6s  %-6s  %-6s  %-6s  %-6s"
    headings = ('sched', 'placemt', 'util', 'cores', 'vhosts', 'target',
                'mean', 'min', 'max', 'stdev', 'maxerr')
    dashes = tuple( [ re.sub('.', '-', h) for h in headings ] )
    print format % headings
    print format % dashes
    
    for opts, runs in results:
        sched = opts['sched']
        static = 'static' if opts['static'] else 'dyn'
        for run in runs:
            hosts = len(run)
            cpucount = int( run[0]['cpucount'] )
            cpulimit = float( run[0]['cpulimit'] )
            util = cpulimit * hosts / cpucount * 100.0
            # Note: we're compressing two dimensions here,
            # time and host!
            samples = sum( [ r['cpuvals'] for r in run], [] )
            r_mean = sum( samples ) / len( samples )
            r_min = min( samples )
            r_max = max( samples )
            r_dev = sigma( samples )
            r_err = max( abs( cpulimit - r_min ), abs( r_max - cpulimit ) )
            # Output
            print format % (
                sched, static, '%.0f%%' % util , cpucount, hosts,
                '%.4f' % cpulimit,
                '%.4f' % r_mean, '%.4f' % r_min, '%.4f'%  r_max,
                '%.4f' % r_dev, '%.4f' % r_err)


def dumpResults( results ):
    "Dump results as text for debugging purposes"
    for opts, runs in results:
        print "Options:", opts
        print "Found", len(runs), "Runs:"
        for r in range(0, len(runs)):
            run = runs[ r ]
            hosts = len( run )
            cpulimit = run[ 0 ][ 'cpulimit' ]
            print "Run %d: %d hosts, cpulimit = %.2f" % (
                r, hosts,  cpulimit )
            for host in run:
                assert cpulimit == host[ 'cpulimit' ]
                print "cpu samples:", host[ 'cpuvals' ]
                print "time:", host[ 'xvals' ]


def table( plotopts, results, tex=False):
    "Print table of sample mean, min and max"

    def output( s ):
        if tex:
            s = re.sub( '%', '\%', s)
            s = re.sub( '_', '\_', s)
        print s
            
    format = ("%-7s  %-5s  %-6s  "
              # "%-6s  %-6s  " 
              "%-6s  %-6s  %-6s" )
    headings = ('sched', 'util', 'goal',
                'mean', 'maxerr', 
                # 'maxerr%', 
                #'rmserr', 
                'rmserr')
    units= ('', '', 'cpu%', 'cpu%', 'cpu%', '%' )
    
    dashes = tuple( [ re.sub('.', '-', h) for h in headings ] )
    
    cores, static, hosts = None, None, None
    for opts, runs in results:
        if not static: 
            static = opts['static']
        else:
            assert static == opts['static']
        if not cores:
            cores = int( runs[0][0]['cpucount'] )
        else:
            assert cores == int( runs[0][0]['cpucount'] )
        if not hosts:
            hosts = len( runs[0] )
        else:
            assert hosts == len( runs[ 0 ] )
    
    static = 'static' if static else 'dynamic'
    
    print
    caption = "%s cores, %s vhosts, %s process placement" % (
        cores, hosts, static)
    if tex:
        caption = r'\caption{%s}' % caption
    output( caption )
    
    if tex:
        fields = len( re.findall( '[^\s]+', format) )
        fields = '| ' + '| '.join(['l '] * fields) + ' |'
        heading = r"\begin{tabular}{ %s }" % fields
        format = '  ' + re.sub('  ', ' & ', format) + r' \\'
        footer = r'\end{tabular}' + '\n'
        output( heading )
        print '  \hline'
        output( format % headings )
        output( format % units )
        print '  \hline'
    else:
        print format % headings
        print format % units
        print format % dashes
        footer = ''
    
    for opts, runs in results:
        sched = opts['sched']
        sched = { 'none': 'default', 'cfs': 'bwc', 'rt': 'rt' }[
            sched ]
        for run in runs:
            cores = int( run[0]['cpucount'] )
            cpulimit = float( run[0]['cpulimit'] ) * 100.0
            util = cpulimit * hosts / cores
            # Note: we're compressing two dimensions here,
            # time and host!
            samples = sum( [ r['cpuvals'] for r in run ], [] )
            # Convert from CPU seconds/second to percent of one core
            samples = [ s * 100.0 for s in samples ]
            r_mean = sum ( samples ) / len( samples )
            r_min = min( samples )
            r_max = max( samples )
            r_dev = sigma( samples )
            r_err = max( abs( cpulimit - r_min ), abs( r_max - cpulimit ) )
            r_err_pct = r_err/cpulimit * 100.0
            r_rmse = rmse( samples, cpulimit )
            r_rmse_pct = r_rmse/cpulimit * 100.0
            # Output
            output( format % (
                            sched, '%.0f%%' % util ,
                            '%.2f' % cpulimit,
                            '%.2f' % r_mean,
                            '%.2f' % r_err,
                            # '%.1f%%' % r_err_pct,
                            #% '%.2f' % r_rmse,
                            '%.1f' % r_rmse_pct ) )
            sched = ''
        if tex:
            print '  \hline'
    
    print footer
                            
def plotVariance( plotopts, results ):
    "Plot CPU utilization variance over time "
    fig = plt.figure( 2 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    defaults = { 'color': 'black' }  # was: { 'linewidth': 2 }
    totals = {}

    ax = fig.add_subplot( 111 )
    ax.yaxis.grid( True )

    xvals = []
    yvals = []
    data = {}  # data[x] = y vals
    for opts, results in order_results(results):
        lines = {}  # lines[hosts] = [[x1, y1], [x2, y2]]
        i = 0
        for hosts in opts['counts']:
            lines[hosts] = []
            for util in opts['utils']:
                #for record in results:
                record = result[i]
                i += 1
                n = len(record)
    #            if (len(plotopts.counts) > 0) and (n not in plotopts.counts):
    #                continue
                values = []
                for r in record:
                    values += r['cpuvals']
                
                lines[hosts].append([util, values])
                cpu = util / float(n)
                exp_value = util / float(hosts)
                x = "%i,%0.2f" % (hosts, util)
                xvals.append(x)
                if plotopts.norm:
                    y = [float(v) / exp_value for v in values]
                else:
                    y = values
                yvals.append(y)
                data[x] = y

    ax.boxplot( yvals )
    ax.set_xticklabels( xvals )

    if plotopts.norm:
        plt.title('CPU utilizations (normalized to expected)')
    else:
        plt.title('CPU utilizations')
    plt.ylabel( 'CPU utilization' )
    plt.xlabel( '(hosts, target util)' )
    #plt.ylim(0.0,0.3)
    label = 'cpu isolation'
    # Turn on y grid only
    #ax = fig.add_subplot( 111 )
    ax.yaxis.grid( True )

    # And blast x tick lines
    for l in ax.get_xticklines():
        l.set_markersize( 0 )
    if not plotopts.nolegend:
        plt.legend()
    savePlot(plotopts, 'box')


def plotLines( d, barchart=True, label='run', **plotargs ):
    "Plot an n to many mapping"
    xvals = sorted( d.keys() )
    yvals = [ d[ x ] for x in xvals ]
    ind = np.arange( len( yvals ) )
    width = .35
    indcenter = ind + .5 * width
    plt.xticks( indcenter, [ str( x ) for x in xvals ] )
    # Use box plot unless bar chart was specified
    if not barchart:
        plt.boxplot( yvals )
        return
    # If we only have one run, just plot bars
    if not reduce( and_, [ len( y ) > 1 for y in yvals ] ):
        plt.bar( ind, [ y[ 0 ] for y in yvals ], width )
        return
    # Otherwise, scatter plot points
    # was: plt.plot( ind + .5 * width, yvals, 'o', **plotargs )
    for x, y in zip( indcenter, yvals ):
        plt.plot( [ x ] * len( y ), y, 'o', **plotargs )
    # hack - is there a better way to add legend?
    plt.plot( indcenter[ 0 ], yvals[ 0 ][ 0 ], 'o',
             label=label, **plotargs )
    # And plot a bar chart of the means
    means = [ sum( y ) / len( y ) for y in yvals ]
    plt.bar( ind, means, width, label='mean' )

def order_results(results):
    # Sort by number of hosts, in decreasing order since we expect higher
    # numbers of hosts to have greater variance, and we want the top-to-bottom
    # order of the legend to match the graph.
    return sorted(results, key=lambda x: x[0]['counts'][0], reverse=True)

def plotAllVariances( plotopts, results ):
    "Plot CPU utilization variance over time "
    fig = plt.figure( 2 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    defaults = { 'color': 'black' }  # was: { 'linewidth': 2 }


    if plotopts.metric == 'sigma':
        #plt.title('Mininet: CPU utilization std dev')
        plt.ylabel( 'sigma', fontsize = FONTSIZE )
        plt.xlabel( 'CPU utilization', fontsize = FONTSIZE )
    elif plotopts.metric == 'cv':
        #plt.title('Mininet: CPU utilization std dev')
        plt.ylabel( 'coefficient of variation', fontsize = FONTSIZE)
        plt.xlabel( 'CPU utilization', fontsize = FONTSIZE )
    #plt.ylim(0.0,0.3)
    label = 'cpu isolation'
    #dictPlot( totals, barchart=plotopts.bar, label=label, **defaults )

    # Turn on y grid only
    ax = fig.add_subplot( 111 )
    ax.yaxis.grid( True )

    for r in order_results(results):
        opts, result = r[0], r[1:]
        lines = {}  # lines[hosts] = [[x1, y1], [x2, y2]]
        i = 0
        for hosts in opts['counts']:
            lines[hosts] = []
            for util in opts['utils']:
                record = result[i]
                i += 1
                n = len(record)
                values = []
                for r in record:
                    print 'ENTRY',r
                    values += r['cpuvals']
                if plotopts.metric == 'sigma':
                    lines[hosts].append([util, sigma(values)])
                elif plotopts.metric == 'cv':
                    lines[hosts].append([util, coeff_var(values)])

        for hosts in opts['counts']:
            data = lines[hosts]
            x = [d[0] for d in data]
            y = [d[1] for d in data]
            ax.plot(x, y, label = "%s hosts" % hosts, linewidth = 1)

        min_x = opts['utils'][0] if not plotopts.minx else plotopts.minx
        max_x = opts['utils'][-1]
        ax.set_xlim([min_x, max_x])

    if plotopts.maxy:
        ax.set_ylim([0, plotopts.maxy])

    # And blast x tick lines
    for l in ax.get_xticklines():
        l.set_markersize( 0 )
    if not plotopts.nolegend:
        plt.legend(loc='upper right')
    
    if plotopts.metric == 'sigma':
        savePlot(plotopts, 'all_sigma')
    elif plotopts.metric == 'cv':
        savePlot(plotopts, 'all_cv')


def colorGenerator():
    "Return cycling list of colors"
    colors = [ 'red', 'green', 'blue', 'purple', 'orange', 'cyan']
    index = 0
    while True:
        yield colors[ index ]
        index = ( index + 1 ) % len( colors )

def linkLegend( cgen, colors, label):
    "Return color and label for link count or '' if already used"
    if label not in colors:
        color = colors[ label ] = cgen.next()
    else:
        color, label = colors[label], ''
    return color, label

def dictPush( d, key, entry ):
    "Append a new element into a dictionary of lists"
    d[ key ] = d.get( key, [] ) + [ entry ]

def dictAppend( d, key, entries, label='runs' ):
    "Append an new list of entries into a dictionary of lists"
    d[ key ] = d.get( key, [] ) + entries
    
def dictPlot( d, barchart=True, label='run', **plotargs ):
    "Plot an n to many mapping"
    xvals = sorted( d.keys() )
    yvals = [ d[ x ] for x in xvals ]
    ind = np.arange( len( yvals ) )
    width = .35
    indcenter = ind + .5 * width
    plt.xticks( indcenter, [ str( x ) for x in xvals ] )
    # Use box plot unless bar chart was specified
    if not barchart:
        plt.boxplot( yvals )
        return
    # If we only have one run, just plot bars
    if not reduce( and_, [ len( y ) > 1 for y in yvals ] ):
        plt.bar( ind, [ y[ 0 ] for y in yvals ], width )
        return
    # Otherwise, scatter plot points
    # was: plt.plot( ind + .5 * width, yvals, 'o', **plotargs )
    for x, y in zip( indcenter, yvals ):
        plt.plot( [ x ] * len( y ), y, 'o', **plotargs )
    # hack - is there a better way to add legend?
    plt.plot( indcenter[ 0 ], yvals[ 0 ][ 0 ], 'o',
             label=label, **plotargs )
    # And plot a bar chart of the means
    means = [ sum( y ) / len( y ) for y in yvals ]
    plt.bar( ind, means, width, label='mean' )


def readData( files ):
    """Read input data from CPUIsolationSweep run
    
    Each run generates a file, which is a set of lines with:
    - a comment
    - a dict of params
    - a list of experiment results

    Return a list consisting of (opts, results) for each file.
    """
    all_results = []
    for file in files:
        results = []
        for line in fileinput.input( file ):
            if line[ 0 ] == '#':
                continue
            data = loads( line )
            if type( data ) == dict:
                opts = loads(line)
            elif type( data ) == list:
                results.append(data)
        all_results.append((opts, results))
    return all_results


def savePlot(opts, plot_name):
    if(opts.dir == ''):
        return
    file_prefix = (os.path.splitext(os.path.basename(opts.args[0]))[0] 
                    if opts.prefix == '' else opts.prefix)
    fname = '%s/%s_%s.png' % (opts.dir, file_prefix, plot_name)
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
    parser.add_option( '-t', '--type',
                      type='string', default='lines', 
                      help='plot type [box|lines|time]' )
    parser.add_option( '-m', '--metric',
                      type='string', default='sigma', 
                      help='metric to plot [sigma|cv]' )
    parser.add_option( '-n', '--nolegend', dest='nolegend',
                      default=False, action='store_true',
                      help="don't add legend to plots" )
    parser.add_option( '-b', '--bar', dest='bar',
                      default=False, action='store_true',
                      help="use bar charts rather than box plots" )
    parser.add_option( '--no-norm', dest = 'norm',
                      default=True, action='store_false',
                      help="normalize variances to expected?" )
    parser.add_option( '--minx', type='float', default=None,
                       help='min X override' )
    parser.add_option( '--maxy', type='float', default=None,
                       help='max Y override' )
    parser.add_option( '-c', '--counts', dest='counts',
        action='callback', callback=intListCallback, default=[],
        type='string',
        help='specify pair counts, e.g. 10,20,40' )
    ( options, args ) = parser.parse_args()
    plotFlags = [ 'var', 'series']
    if options.prefix != '' and options.dir == '':
        print 'WARNING: "prefix" option will be ignored without the "dir" option'

    return options, args


if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args
    all_results = readData( files=args )
    dumpResults( all_results )

    if plotopts.type == 'box':
        plotVariance( plotopts, all_results )
    elif plotopts.type == 'time':
        plotIntervals( plotopts, all_results )
    elif plotopts.type == 'lines':
        plotAllVariances( plotopts, all_results )
    elif plotopts.type == 'table':
        table( plotopts, all_results )
    elif plotopts.type == 'tex':
        table( plotopts, all_results, tex=True )
    else:
        raise Exception("unknown plot type")
    if(plotopts.dir == ''):
        plt.show()

