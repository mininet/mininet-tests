
import csv, pprint, numpy, sys
import numpy as np

import matplotlib as m
m.use('SVG')
import matplotlib.pyplot as plt


fields = ['timer', 'count', 'latency']
MEG = 1e6
def read_csv_file(fname):
  f = open(fname,'r')
  d = csv.DictReader(f, fieldnames=fields)
  ret = list(d)
  f.close()
  return ret

def save_plot(values, t, fname):
  plt.figure()
  ax = plt.subplot(111)
  plt.title('Timer latency; close to 0/uniform is preferable\n' +
    'y-axis is log-scale, as a fraction of the timer value t=%d us' % t)
  plt.ylabel('Latency')
  ax.set_yscale('log')
  plt.xlabel('Trial#')
  ax.plot(xrange(0, len(values)), values, 'o')
  """hist = plt.hist(values, 
    bins=bins,
    histtype='step',
    normed=1, 
    facecolor='green', 
    alpha=0.75)"""
  plt.savefig(fname)
  plt.clf()

def stats(data):
  timers = set(int(r['timer']) for r in data)
  ret = []
  for t in sorted(timers):
    stat = {}
    # damn slow, but doesnt matter
    counts = [int(r['count']) for r in data if int(r['timer']) == t]
    latencies = [float(r['latency']) for r in data if int(r['timer']) == t]
    latencies = map(lambda x: x / (t / MEG), latencies)
    
    save_plot(latencies, t, "latency_%d.svg" % t)

    stat.update({ t : [
      ('count_min', numpy.min(counts)),
      ('count_max', numpy.max(counts)),
      ('count_std', numpy.std(counts)),
      ('ltncy_min', numpy.min(latencies)),
      ('ltncy_max', numpy.max(latencies)),
      ('ltncy_std', numpy.std(latencies))
    ]})
    ret.append(stat)
  return ret

if len(sys.argv)>1:
  pprint.pprint(stats(read_csv_file(sys.argv[1])))

