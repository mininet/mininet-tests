#!/usr/bin/python

import matplotlib.pyplot as plt
import numpy as np
from mininet.test.nsdi.plot import colorGenerator
from optparse import OptionParser
import csv
import os
import re

def parse_hedera_csv(plotopts):
    infile = plotopts.args[0]
    f = open(infile, 'r')
    result = {}
    result_reader = csv.reader(f)
    for l in result_reader:
        if (len(l) < 5):
            continue
        key = l[0]
        val = {'nonblocking':float(l[1]), 'fattree':float(l[2])}
        result[key] = val
    return result

def parse_mininet_out(indir, plotopts):
    avg_xput = []
    for infile in os.listdir(indir):
        outfile_re = re.compile('^\d+\.out$')
        if not outfile_re.match(infile):
            continue
        fname = '%s/%s' % (indir, infile)
        f = open(fname, 'r')
        lines = f.readlines()
        assert len(lines) > 20
        vals = []
        for line in lines[10:20]:
            l = line.split()
            if plotopts.tx:
                vals.append(float(l[2]))
            else:
                vals.append(float(l[1]))
        avg_xput.append(sum(vals)/len(vals))
    return sum(avg_xput)

def parseOptions():
    "Parse command line options"
    parser = OptionParser( 'usage: %prog [options] [hedera csv file]' )
    parser.add_option( '-t', '--tx', dest='tx',
                      default=False, action='store_true',
                      help='plot tx rate at the switch interfaces' )
    parser.add_option( '-r', '--runs', dest='runs',
        type='int', default=10, help='specify number of runs of each test' )
    parser.add_option( '-b', '--bw', dest='bw',
        type='int', default=100, help='bandwidth of each link' )
    parser.add_option( '-m', '--map', dest='map',
                      type='string', default='hedera/traffic_to_input.csv', 
                      help='traffic pattern to input directory map' )
    parser.add_option( '-i', '--indir', dest='indir',
                      type='string', default='', 
                      help='input directory to read data from' )
    parser.add_option( '-o', '--output', dest='output',
                      type='string', default='', 
                      help='output plot to file"' )
    ( options, args ) = parser.parse_args()
    return options, args
    
if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args
    assert len(plotopts.args) > 0

    # parse traffic2input map csv
    traffic2input_f = open(plotopts.map, 'r')
    traffic2input = {}
    csv_reader = csv.reader(traffic2input_f)
    traffic = []
    for l in csv_reader:
        if (len(l) < 2):
            continue
        traffic.append(l[0])
        traffic2input[l[0]] = l[1]

    print ' '.join([traffic2input[k] for k in traffic[:20]])

    #parse hedera results
    hedera_result = parse_hedera_csv(plotopts)

    num_t = 20 # plot just the first 20 results

    mininet_result = []
    qlens = range(10, 200, 20) + [5000]
    for j in range(plotopts.runs):
        # parse mininet results
        mininet_result.append({})
        for t in traffic[:num_t]:
            mininet_result[j][t] = {}
            for q in qlens:
                nonblocking_dir = '%s/nonblocking-100mbps-q%d/%d/%s' % (plotopts.indir, q, j+1, traffic2input[t])
                
                nonblocking_val = parse_mininet_out(nonblocking_dir, plotopts)
                mininet_result[j][t][q] = nonblocking_val

    hedera_fbb = 16000.0 #16 gbps
    mininet_fbb = 16. * plotopts.bw #1600 mbps

    cgen = colorGenerator()
    for t in traffic[:20]:
        color = cgen.next()
        x = qlens
        # hedera nonblocking
        hedera_y = [hedera_result[t]['nonblocking']/hedera_fbb] * len(x)
        plt.plot(x, hedera_y, '--', color=color, label='Hedera:%s'%t)

        # mininet nonblocking
        nonblocking_yvals = [[mininet_result[j][t][q]/mininet_fbb for j in range(plotopts.runs)] for q in x]
        mininet_y = [sum(l)/len(l) for l in nonblocking_yvals]
        yerr_lo = [mininet_y[j] - min(nonblocking_yvals[j]) for j in range(len(nonblocking_yvals))]
        yerr_hi = [max(nonblocking_yvals[j]) - mininet_y[j] for j in range(len(nonblocking_yvals))]
        plt.errorbar(x, mininet_y, yerr=[yerr_lo, yerr_hi], ecolor=color, label='Mininet:%s'%t)

    plt.ylim(0.0, 1.0)
    plt.ylabel('Normalized Throughput')
    plt.xlabel('Queue size (pkts)')
    #plt.legend(loc='lower right')
    plt.show()

