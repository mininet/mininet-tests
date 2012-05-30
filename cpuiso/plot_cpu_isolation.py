#!/usr/bin/python

import fileinput
from math import sqrt
from json import loads
from optparse import OptionParser
from sys import exit
from operator import and_, add
import os
import re

# We use python-matplotlib and numpy for graphing
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Accumulate results and calculate variance

def trunc2( x ):
    "Quantize to lower .5"
    return int( x * 2 ) / 2

def accumulateIntervals( opts,  entries, field ):
    """Accumulate results and return list of (start, stop, mbps)"""
    bws = {}
    totalbw = {}
    variance = {}
    for entry in entries:
        intervals = entry[ field ]
        for start, stop, bw in intervals:
            # Accumulate into 1 second bins
            # It's hard to do this right
            binstart = int( start )
            binend = binstart + 1
            if stop <= binend:
                # easy case - contained by interval
                bws[ binstart ] = bws.get( binstart, [] ) + [ bw ]
            elif stop > binend and stop < binend + 1:
                # harder case - split over end of interval
                bw1 = bw * ( binend - start )
                bw2 = bw * ( stop - binend )
                bws[ binstart ] = bws.get( binstart, [] ) + [ bw1 ]
                bws[ binend ] = bws.get( binend, [] ) + [ bw2 ]
            else:
                print "ignoring large interval:", start, stop
    for key in bws.keys():
        totalbw[ key ] = sum( bws[ key ] )  # Correct
        variance[ key ] = sigma2( bws[ key ] )   # Not really correct
    accumulated = [ ( key, key + 1,  totalbw[ key ], variance[ key ] )
                   for key in sorted( totalbw.keys() ) ]
    return accumulated

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

def rmse( nums, expected ):
    "Calculate sqrt( sum( (x[i] - expected)^2 ) / n ) "
    n = len( nums )
    sumsq = sum( [ (x - expected) * (x - expected) for x in nums ] )
    mse = sumsq / n
    result = sqrt( mse )
    return result

def accumulateLinkBw( results ):
    "Accumulate overall link bandwidth, reported by iperf"
    bws = [ bps for src, dest, result, bps in results ]
    totalbw = sum( bws )
    stdev = None  # was: sigma( bws )
    return totalbw, stdev

def calculateTotals( opts, results ):
    "Calculate total bps over multiple links"
    totals = []
    for r in results:
        pairs, entries = r[ 'pairs' ], r[ 'results' ]
        # Ugly - should clean this up -BL
        if opts.iperf:
            intervals = r[ 'iperfIntervalTotals' ] = [ { 'entries':
                accumulateIntervals( opts, entries, 
            'iperfIntervals(start,stop,mbps)') } ]
        if opts.rxbytes:
            r[ 'rxIntervalTotals' ] = [ { 'entries':
                accumulateIntervals( opts, entries, 'rxBwIntervals' ) } ]

def plotIntervals( plotopts, results ):
    "Plot iperf bandwidth over time "
    fig = plt.figure( 1 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    defaults = {}  # was: { 'linewidth': 2 }
    cgen, colors = colorGenerator(), {}
    for opts, result in results:
        for record in result:
            n = len(record)
            if (len(plotopts.counts) > 0) and (n not in plotopts.counts):
                continue
            for r in record:
                xvals, cpuvals = r['xvals'], r['cpuvals']
                cpulimit = r.get( 'cpulimit', None )
                # plot!
                color, label = linkLegend( cgen, colors, n, opts)
                plt.plot( xvals, cpuvals, label=label, color=color, **defaults )
                if cpulimit:
                    plt.axhline( y=cpulimit, linestyle=':', color='black', 
                        linewidth=2 )
    plt.title('CPU utilization')
    plt.ylabel( 'CPU seconds/second' )
    plt.xlabel( 'Time (s)' )
    if not plotopts.zoom:
            plt.ylim(0.0, 1.0)
    plt.grid( True )
    plt.legend()
    savePlot(plotopts, 'timeseries')


def oldtable( plotopts, results ):
    "Print table of sample mean, min and max"
    
    format = "%-5s %-7s %-4s %-6s %-6s  %-6s  %-6s  %-6s  %-6s  %-6s  %-6s"
    headings = ('sched', 'placemt', 'util', 'cores', 'vhosts', 'target',
                'mean', 'min', 'max', 'maxerr', 'stdev')
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
            r_err = max( abs( cpulimit - r_min ), abs( r_max - cpulimit ) )
            r_dev = sigma( samples )
            # Output
            print format % (
                sched, static, '%.0f%%' % util , cpucount, hosts,
                '%.4f' % cpulimit,
                '%.4f' % r_mean, '%.4f' % r_min, '%.4f'%  r_max,
                '%.4f' % r_err, '%.4f' % r_dev)




def table( plotopts, results, tex=False):
    "Print table for paper"
    
    def output( s ):
        if tex:
            s = re.sub( '%', '\%', s)
            s = re.sub( '_', '\_', s)
        print s

    format = ("%-7s  %-6s  %-6s  "
              # "  %-6s  %-6s" 
              "%-6s  %-6s  %-6s" )
              
    
    headings = ('sched', 'vhosts', 'goal',
                'mean', 'maxerr', 
                # 'maxerr', 
                #'rmserr', 
                'rmserr')
    
    units = ('', '', 'cpu%', 'cpu%', 'cpu%', '%' )
    
    dashes = format % tuple( [ re.sub('.', '-', h) for h in headings ] )

    cores, static, util = None, None, None
    for opts, runs in results:
        if not static: 
            static = opts['static']
        else:
            assert static == opts['static']
        if not cores:
            cores = int( runs[0][0]['cpucount'] )
        else:
            assert cores == int( runs[0][0]['cpucount'] )
        if not util:
            util = float( opts[ 'cpu' ] )
        else:
            assert util == float( opts[ 'cpu'] )
    
    static = 'static' if static else 'dynamic'
    
    print
    caption = "%s cores, %.0f%% target utilization, %s process placement." % (
        cores, util * 100.0 , static )
    if tex:
        caption = r'\caption{%s}' % caption
    output( caption )

    if tex:
        fields = len( re.findall( '[^\s]+', format) )
        fields = '| ' + '| '.join(['l '] * fields) + ' |'
        heading = r"\begin{tabular}{ %s }" % fields
        format = '  ' + re.sub('  ', ' & ', format) + r' \\'
        footer = r'  \hline' + '\n' + r'\end{tabular}' + '\n'
        output( heading )
        print '  \hline'
        output( format % headings )
        output( format % units )
    else:
        print
        print format % headings
        print format % units
        print dashes
        footer = ''

    oldsched = ''
    for opts, runs in results:
    
        sched = { 'none': 'default', 'cfs': 'bwc', 'rt': 'rt' }[
            opts['sched'] ]
        if sched != oldsched:
            oldsched = sched
            if tex:
                print '  \hline'
        else: 
            sched = ''

        for run in runs:
            hosts = len(run)
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
                            sched,  hosts,
                            '%.2f' % cpulimit,
                            '%.2f' % r_mean,
                            '%.2f' % r_err,
                            # '%.1f%%' % r_err_pct,
                            #% '%.2f' % r_rmse,
                            '%.1f' % r_rmse_pct ) )



    print footer
                            
def plotVariance( plotopts, results ):
    "Plot CPU utilization variance over time "
    fig = plt.figure( 2 )
    fig.canvas.set_window_title( 'Mininet: ' + 
                                str( plotopts.args ) )
    defaults = { 'color': 'black' }  # was: { 'linewidth': 2 }
    totals = {}
    for record in results:
        n = len(record)
        if (len(plotopts.counts) > 0) and (n not in plotopts.counts):
            continue
        for r in record:
            dictAppend(totals, n, r['cpuvals'])
    plt.title('Mininet: CPU utilization variance')
    plt.ylabel( 'CPU Fraction' )
    plt.xlabel( 'No. of Nodes' )
    plt.ylim(0.0,0.3)
    label = 'cpu isolation'
    dictPlot( totals, barchart=plotopts.bar, label=label, **defaults )
    # Turn on y grid only
    ax = fig.add_subplot( 111 )
    ax.yaxis.grid( True )
    # And blast x tick lines
    for l in ax.get_xticklines():
        l.set_markersize( 0 )
    if not plotopts.nolegend:
        plt.legend()
    savePlot(plotopts, 'variance')


def colorGenerator():
    "Return cycling list of colors"
    colors = [ 'red', 'green', 'blue', 'purple', 'orange', 'cyan']
    index = 0
    while True:
        yield colors[ index ]
        index = ( index + 1 ) % len( colors )

def linkLegend( cgen, colors, nodes, opts):
    "Return color and label for link count or '' if already used"
    sched = opts.get( 'sched', '' )
    cores = opts.get( 'cores', '' )
    static = 'static' if opts['static'] else 'dyn'
    util = float( opts['cpu'] ) * 100.0 
    key = '%sp*%.0f%%/%sh-%s-%s' % (cores, util, nodes, sched, static)
    if key not in colors:
        color = colors[ key ] = cgen.next()
        label = key
    else:
        color, label = colors[key], None
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

# Parse command line options and dump results

def intListCallback( option, opt, value, parser ):
    "Callback for parseOptions"
    value = [ int( x ) for x in value.split( ',' ) ]
    setattr( parser.values, option.dest, value )

def parseOptions():
    "Parse command line options"
    parser = OptionParser( 'usage: %prog [options] [input files]' )
    parser.add_option( '-d', '--dir', dest='dir',
                      type='string', default='', 
                      help='save plots in the directory "dir"' )
    parser.add_option( '-p', '--prefix', dest='prefix',
                      type='string', default='', 
                      help='custom prefix for saved figures' )
    parser.add_option( '-s', '--series', dest='series',
                      default=False, action='store_true',
                      help='plot individual cpu utilizations as a time-series' )
    parser.add_option( '-v', '--var', dest='var',
                      default=False, action='store_true',
                      help='plot cpu utilization variance' )
    parser.add_option( '-t', '--table', dest='table',
                      default=False, action='store_true',
                      help='print ascii table of statistics' )
    parser.add_option( '-x', '--tex', dest='tex',
                      default=False, action='store_true',
                      help='print TeX table of statistics' )
    parser.add_option( '-n', '--nolegend', dest='nolegend',
                      default=False, action='store_true',
                      help="don't add legend to plots" )
    parser.add_option( '-b', '--bar', dest='bar',
                      default=False, action='store_true',
                      help="use bar charts rather than box plots" )
    parser.add_option( '-a', '--all', dest='all',
                      default=False, action='store_true',
                      help='create all available plots' )
    parser.add_option( '-c', '--counts', dest='counts',
        action='callback', callback=intListCallback, default=[],
        type='string',
        help='specify pair counts, e.g. 10,20,40' )
    parser.add_option( '-z', '--zoom', dest='zoom',
                      default=False, action='store_true',
                      help='use zoomed rather than fixed y axis')
    
    ( options, args ) = parser.parse_args()
    plotFlags = [ 'var', 'series']
    if options.prefix != '' and options.dir == '':
        print 'WARNING: "prefix" option will be ignored without the "dir" option'
    if options.all:
        for opt in plotFlags:
            if getattr( options, opt ) is False:
                setattr( options, opt,  True )
    doPlots = options.var or options.series or options.table or options.tex
    if not doPlots:
        print 'No plots selected - please select a plot option.'
        parser.print_help()
        exit( 1 )
    return options, args

def readData( files ):
    "Read input data from pair_intervals run"
    results = []
    opts, entries = {}, []
    for line in fileinput.input( files ):
        if line[ 0 ] == '#':
            continue
        data = loads( line )
        if type( data ) == dict:
            if entries:
                results.append( (opts, entries ) )
            opts, entries = data, []
        elif type( data ) == list:
            entries.append(data)
    if entries:
        results.append( ( opts, entries ) )
    return results


def savePlot(opts, plot_name):
    if(opts.dir == ''):
        return
    file_prefix = os.path.splitext(os.path.basename(opts.args[0]))[0] if opts.prefix == '' else opts.prefix
    fname = '%s/%s-%s.png' % (opts.dir, file_prefix, plot_name)
    print 'Saving plot to %s' % fname
    plt.savefig(fname)

    
if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args
    results = readData( files=args )
    if plotopts.series:
        plotIntervals( plotopts, results )
    if plotopts.var:
        plotVariance( plotopts, results )
    if plotopts.table:
        table( plotopts, results )
    if plotopts.tex:
        table( plotopts, results, tex=True )
    if (plotopts.dir == '' and (plotopts.series or plotopts.var)):
        plt.show()

