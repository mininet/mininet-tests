#!/usr/bin/python

import fileinput
from json import loads
from optparse import OptionParser
from sys import exit
from operator import and_, add
import os
import re
import math
from subprocess import check_output
import sys

sys.path.append('..')

import matplotlib.pyplot as plt
from cpuiso.CPUIsolationLib import intListCallback
from util.plot import colorGenerator
from lib.helper import avg, stdev
from mininet.util import quietRun
import util.plot_defaults

def sh( cmd ):
    return check_output(cmd, shell=True)

def startplot():
    plt.figure(1)
    
def finishplot():
    # plt.title('iperf bandwidth under load')
    plt.ylabel('TCP throughput A to B (Mb/s)')
    plt.yscale('log')
    plt.xlabel('Additional busy hosts')
    plt.grid()
    plt.legend() # (loc=3)
    plt.savefig('emulab.pdf')
    plt.show()

def readdata( fname ):
    rawbw = sh( 'tail -30 %s | grep "0.0-[0-9][0-9]"' % fname )
    print rawbw
    r = r'(\d+\.?\d+) (.bits)/sec'
    bws = []
    for bw, unit in re.findall( r, rawbw ):
        f = float(bw)
        if 'Gbits' in unit:
            f *= 1000.0
        elif 'Kbits' in unit:
            f *= .001
        elif 'Mbits' in unit:
            pass
        elif ' bits' in unit:
            f *= 1e-6
        else:
            raise Exception('readdata: unknown bandwidth unit')
        bws.append( f )
    rawload = sh( 'grep load %s' % fname )
    loads = re.findall( r'(\d+) load', rawload )
    loads = [ int(load) for load in loads ]
    return loads, bws

def plot( label, fname, sym='+-' ):
    loads, bws = readdata( fname )
    print len(loads), loads
    print len(bws), bws
    plt.plot( loads, bws, sym, label=label, linewidth=2 )    
    
if __name__ == '__main__':
    startplot()
    plot('Mininet', 'good/emulab-rhone-1p-none-None-None.out', 'o-')
    #plot('mininet+cpu', 'emulab-rhone-1p-cfs-0.09-None.out')
    #plot('mininet+bw', 'emulab-rhone-1p-none-None-200.out')
    plot('vEmulab', 'good/test-6.out', 'v-')
    plot('"ideal"', 'good/emulab-rhone-1p-cfs-0.09-200.out', 's--')
    finishplot()
