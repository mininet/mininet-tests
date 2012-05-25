from helper import *
import argparse

import sys
sys.path.append(os.path.abspath('mininet-nsdi'))

import dctcp_hardware, dctcp_mininet
import tcp_hardware, tcp_mininet

def normalise(values, interval=0.125):
    xvalues = []
    yvalues = []
    time = 0
    for v in values:
        time += interval
        if time >= 10 and time <= 25:
            xvalues.append(time)
            yvalues.append(v)
    return xvalues, yvalues

def plot(blah, interval, label):
    xs, ys = normalise(blah, interval)
    plt.plot(xs, ys, label=label, lw=2)

plot(dctcp_hardware.q_dctcp_hardware, 0.125, "DCTCP-hardware")
plot(dctcp_mininet.q_dctcp_mininet, 0.01, "DCTCP-mininet")

plot(tcp_hardware.q_tcp_hardware, 0.125, "TCP-hardware")
plot(tcp_mininet.q_tcp_mininet, 0.01, "TCP-mininet")

plt.title("TCP,DCTCP: Hardware, Mininet")
plt.xlabel("Time (s)")
plt.ylabel("Instantaneous queue occupancy (KB)")
plt.grid(True)
plt.legend()

plt.figure()
plt.show()

