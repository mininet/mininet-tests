#!/usr/bin/python

import sys
sys.path = ['../'] + sys.path

import matplotlib.pyplot as plt
import numpy as np
from util.plot_defaults import *
from util.plot import colorGenerator, hatchGenerator
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
        #outfile_re = re.compile('^\d+\.out$')
        outfile_re = re.compile('^\d+\_\d+\_\d+\.out$')
        if not outfile_re.match(infile):
            continue
        fname = '%s/%s' % (indir, infile)
	print fname
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
    parser.add_option( '-s', '--suffix', dest='suffix',
                      type='string', default='', 
                      help='add suffix to input directory"' )
    ( options, args ) = parser.parse_args()
    return options, args
    
if __name__ == '__main__':
    plotopts, args = parseOptions()
    plotopts.args = args
    assert len(plotopts.args) > 0

    veth_correction = 1514./(1514+8+4+12)

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

    run_range = range(plotopts.runs)

    mininet_result = []
    for j in run_range:
        # parse mininet results
        mininet_result.append({})
        for t in traffic[:num_t]:
            nonblocking_dir = '%s/nonblocking%s/%d/%s' % (plotopts.indir, plotopts.suffix, j+1, traffic2input[t])
            fattree_dir = '%s/fattree%s/%d/%s' % (plotopts.indir, plotopts.suffix, j+1, traffic2input[t])
            
            nonblocking_val = parse_mininet_out(nonblocking_dir, plotopts)
            fattree_val = parse_mininet_out(fattree_dir, plotopts)
            mininet_result[j][t] = {'nonblocking':nonblocking_val, 'fattree':fattree_val}

    hedera_fbb = 16000.0 #16 gbps
    mininet_fbb = 16. * plotopts.bw #1600 mbps
    num_plots = 2 # divide the plot into 2 figures
    nt = num_t/num_plots
    for i in range(num_plots):
        fig = plt.figure(i+1)
        cgen = colorGenerator()
        hgen = hatchGenerator()

        tt = traffic[i*nt:(i+1)*nt]
        ind = np.arange(nt)
        width = 0.2

        # hedera fattree
        y = [hedera_result[t]['fattree']/hedera_fbb for t in tt]
        p1 = plt.bar(ind + 0.5*width, y, width, color=cgen.next(), hatch=hgen.next())

        # mininet fattree
        fattree_yvals = [[mininet_result[j][t]['fattree']*veth_correction/mininet_fbb for j in run_range] for t in tt]
        y = [sum(l)/len(l) for l in fattree_yvals]
        yerr_lo = [y[j] - min(fattree_yvals[j]) for j in range(len(fattree_yvals))]
        yerr_hi = [max(fattree_yvals[j]) - y[j] for j in range(len(fattree_yvals))]
        p2 = plt.bar(ind + 1.5*width, y, width, color=cgen.next(), hatch=hgen.next())
        plt.errorbar(ind + 2.0*width, y, yerr=[yerr_lo, yerr_hi], elinewidth=3, fmt='k.')

        # hedera nonblocking
        y = [hedera_result[t]['nonblocking']/hedera_fbb for t in tt]
        p3 = plt.bar(ind + 2.5*width, y, width, color=cgen.next(), hatch=hgen.next())

        # mininet nonblocking
        nonblocking_yvals = [[mininet_result[j][t]['nonblocking']*veth_correction/mininet_fbb for j in run_range] for t in tt]
        y = [sum(l)/len(l) for l in nonblocking_yvals]
        yerr_lo = [y[j] - min(nonblocking_yvals[j]) for j in range(len(nonblocking_yvals))]
        yerr_hi = [max(nonblocking_yvals[j]) - y[j] for j in range(len(nonblocking_yvals))]
        p4 = plt.bar(ind + 3.5*width, y, width, color=cgen.next(), hatch=hgen.next())
        plt.errorbar(ind + 4.0*width, y, yerr=[yerr_lo, yerr_hi], elinewidth=3, fmt='k.')

        plt.ylim(0.0, 1.2)
        plt.ylabel('Normalized Throughput')
        plt.xticks(ind + 0.5, tt, rotation=30)
        plt.legend([p1[0], p2[0], p3[0], p4[0]], 
                ['Hedera-ECMP', 'Mininet-HiFi-ECMP', 'Hedera-NonBlocking', 'Mininet-HiFi-NonBlocking'], loc='upper left')

    plt.show()
