#!/usr/bin/python

import os
from json import loads
import fileinput
import matplotlib.pyplot as plt
import csv
from optparse import OptionParser
from subprocess import Popen

def readData( files ):
    "Read input data from pair_intervals run"
    results = []
    opts = {}
    for line in fileinput.input( files ):
        if line[ 0 ] == '#':
            continue
        data = loads( line )
        if type( data ) == dict:
            opts = loads(line)
        elif type( data ) == list:
            results +=  data
    return results, opts

def parseOptions():
    "Parse command line options"
    parser = OptionParser( 'usage: %prog [options] [hedera csv file]' )
    parser.add_option( '-n', '--node', dest='node',
                      default=False, action='store_true',
                      help='plot individual node CPU util' )
    parser.add_option( '-r', '--runs', dest='runs',
        type='int', default=10, help='specify number of runs of each test' )
    parser.add_option( '-m', '--map', dest='map',
                      type='string', default='hedera/traffic_to_input.csv', 
                      help='traffic pattern to input directory map' )
    parser.add_option( '-i', '--indir', dest='indir',
                      type='string', default='', 
                      help='input directory to read data from' )
    parser.add_option( '-o', '--outdir', dest='outdir',
                      type='string', default='/tmp', 
                      help='output plots to dir"' )
    ( options, args ) = parser.parse_args()
    return options, args

if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args

    if not os.path.isdir(plotopts.outdir):
        os.makedirs(plotopts.outdir)

    # parse traffic2input map csv
    traffic2input_f = open(plotopts.map, 'r')
    traffic2input = {}
    csv_reader = csv.reader(traffic2input_f)
    traffic = []
    num_t = 20 # plot just the first 20 results
    for l in csv_reader:
        if (len(l) < 2):
            continue
        traffic.append(l[0])
        traffic2input[l[0]] = l[1]

    num_fig = 1
    for j in range(plotopts.runs):
        for t in traffic[:num_t]:
            # input directory
            nonblocking_dir = '%s/nonblocking/%d/%s' % (plotopts.indir, j+1, traffic2input[t])
            fattree_dir = '%s/fattree/%d/%s' % (plotopts.indir, j+1, traffic2input[t])

            # output file
            nonblocking_outfile = 'nonblocking-%s-run%d.png' % (traffic2input[t], j+1)
            fattree_outfile = 'fattree-%s-run%d.png' % (traffic2input[t], j+1)

            if plotopts.node:
                print 'Saving plot to: %s/%s' % (plotopts.outdir, nonblocking_outfile)
                results, opts = readData(files=['%s/cpu_usage.json' % nonblocking_dir])
                fig = plt.figure(num_fig)
                num_fig += 1
                for rec in results:
                    for r in rec:
                        plt.plot(r['xvals'], r['cpuvals'])
                plt.savefig('%s/%s' % (plotopts.outdir, nonblocking_outfile))

                print 'Saving plot to: %s/%s' % (plotopts.outdir, fattree_outfile)
                results, opts = readData(files=['%s/cpu_usage.json' % fattree_dir])
                fig = plt.figure(num_fig)
                num_fig += 1
                for rec in results:
                    for r in rec:
                        plt.plot(r['xvals'], r['cpuvals'])
                plt.savefig('%s/%s' % (plotopts.outdir, fattree_outfile))

            else:
                # plot
                print 'Saving plot to: %s/%s' % (plotopts.outdir, nonblocking_outfile)
                Popen('python linktests/plot_cpu.py --files %s/cpu.txt --out %s/%s' % (nonblocking_dir, plotopts.outdir, nonblocking_outfile), shell=True).wait()
                print 'Saving plot to: %s/%s' % (plotopts.outdir, fattree_outfile)
                Popen('python linktests/plot_cpu.py --files %s/cpu.txt --out %s/%s' % (fattree_dir, plotopts.outdir, fattree_outfile), shell=True).wait()
