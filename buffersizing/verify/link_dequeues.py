import sys

sys.path.append('../../util')
from helper import *
import plot_defaults

parser = argparse.ArgumentParser()
parser.add_argument('--files', '-f',
                    help="Dequeue sample files",
                    required=True,
                    action="store",
                    nargs='+',
                    dest="files")

parser.add_argument('--expected',
                    required=True,
                    action="store",
                    nargs='+',
                    dest="expected")

parser.add_argument('--labels',
                    required=True,
                    action="store",
                    nargs='+',
                    dest="labels")

parser.add_argument('--out', '-o',
                    help="Output png file for the plot.",
                    default=None, # Will show the plot
                    dest="out")

parser.add_argument('--title',
                    default="CDF of percentage of inter-dequeue time\ndeviation from that of an ideal link")

parser.add_argument('--ccdf',
                    action="store_true",
                    help="Plot the complementary CDF (CCDF) function.",
                    default=False)

parser.add_argument('--percent',
                    action="store_true",
                    help="y-axis = percent",
                    default=False)

parser.add_argument('--log',
                    action="store_true",
                    help="logscale y-axis.",
                    default=False)

args = parser.parse_args()
#MARKERS='^vos'
PHI=1.618
fig = plt.figure(figsize=(8, 8/PHI))

LINESTYLES=['-','--','-.']

if args.ccdf:
    args.title = args.title.replace("CDF", "CCDF")

def read_samples(f):
    lines = [float(line) for line in open(f).xreadlines()]
    return lines

i = -1
for f,exp,label in zip(args.files, args.expected, args.labels):
    i += 1
    samples = read_samples(f)
    exp = float(exp)
    normalised = [abs(sample / exp - 1.0) * 100.0 for sample in samples]

    x, y = cdf(normalised)
    if args.ccdf:
        y = map(lambda e: 1.0 - e, y)
    plt.plot(x, y, lw=2, label=label, ls=LINESTYLES[i])

if args.ccdf:
    plt.legend()
else:
    plt.legend(loc="lower right")

#plt.xlabel("Percentage deviation from expected", fontsize='large')
plt.xlabel("Percentage deviation from expected")
plt.ylabel("Fraction")
plt.title(args.title)
plt.xscale("log")
plt.ylim((0, 1))
plt.gcf().subplots_adjust(bottom=0.2)

if args.log:
    plt.yscale('log')
    plt.ylim((1e-3, 1))
plt.grid(True)

if args.percent:
    plt.ylabel("Percent")
    locs, labels = plt.yticks()
    labels = []
    for loc in locs:
        labels.append('%d' % (loc * 100))
    plt.yticks(locs, labels)


    locs, labels = plt.xticks()
    replace = True
    labels = []
    for loc in locs:
        labels.append('%d' % (loc * 100))
        if loc * 100 > 1000:
            replace = False
    if replace:
        plt.xticks(locs, labels)

if args.out:
    plt.savefig(args.out)
else:
    plt.show()

