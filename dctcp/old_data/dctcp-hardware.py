import pexpect
from subprocess import Popen
from time import sleep
import sys
import termcolor as T
import re

hosts = {
    'l1': {'ip': '192.168.1.1',
           '_mac': '00:25:90:0c:22:59',
           'col': 'yellow',
           'iname': 'eth1',
           'name': 'A',
           'port': 1,
           },
    'l2': {'ip': '192.168.1.2',
           '_mac': '00:25:90:0c:22:75',
           'col': 'blue',
           'iname': 'eth1',
           'name': 'B',
           'port': 17,
           },
    'l3': {'ip': '192.168.1.3',
           '_mac': '00:25:90:0b:9d:d6 ',
           'col': 'cyan',
           'iname': 'eth0',
           'name': 'C',
           'port': 15
           },
}

def progress(t):
    while t > 0:
        print T.colored('  %3d seconds left  \r' % (t), 'cyan'),
        t -= 1
        sys.stdout.flush()
        sleep(1)
    print '\r\n'

def info(s):
    print s

def config_bcom_switch(enable_red, K=30*1024):
    Popen("ssh alonzo 'rm q.txt; killall -9 minicom'", shell=True).wait()
    prompt = 'BCM.0>'
    K_cells = K / 128
    print 'Broadcom #cells %d' % (K_cells)
    child = pexpect.spawn('ssh -t alonzo minicom -o')
    child.send("\n")
    child.expect(prompt)
    if not enable_red:
        #child.sendline('m wredconfig_cell maxdroprate=0 enable=0')
        #child.expect(prompt)
        # enable red but disable marking (it's effectively drop threshold)
        child.sendline('m wredconfig_cell maxdroprate=0xe enable=0')
        child.expect(prompt)
        child.sendline('m wredparam_cell dropstartpoint=%d dropendpoint=%d' % (K_cells, K_cells))
        child.expect(prompt)
        child.sendline('s ecn_config 0')
        child.expect(prompt)
        info("Disabled RED/ECN")
    else:
        child.sendline('m wredconfig_cell maxdroprate=0xe enable=1')
        child.expect(prompt)
        child.sendline('m wredparam_cell dropstartpoint=%d dropendpoint=%d' % (K_cells, K_cells))
        child.expect(prompt)
        child.sendline('s ecn_config 0xffffff')
        child.expect(prompt)
        info("Enabled RED/ECN")
    child.close(force=True)

def monitor_bcom_qlen(host,name):
    info("Starting queue monitoring on switch port %d of %s (%s)" % (hosts[host]['port'], hosts[host]['name'], host))
    c="ssh alonzo 'export TERM=xterm; rm ~/q-%s.txt; killall -9 minicom; " % name
    c += " perl ~/bcom_qlen.pl %d > ~/q-%s.txt'" % (hosts[host]['port'], name)
    print c
    return Popen(c, shell=True)

def cmd(host, c, wait=False):
    print "%s: %s" % (host, c)
    p = Popen("ssh  %s '%s'" % (host, c), shell=True)
    if wait:
        p.wait()

def set_dctcp(set=False):
    val = 0
    if set:
        val = 1
    for h in hosts.keys():
        cmd(h, "sysctl -w net.ipv4.tcp_dctcp_enable=%d" % val, True)

def runexpt(name,t):
    #cmd("l2", "tc qdisc add dev eth1 root handle 1: netem delay %s" % args.delay)
    #cmd("l3", "tc qdisc add dev eth0 root handle 1: netem delay %s" % args.delay)
    cmd("l1", "iperf -s &")
    dir = "/tmp/%s" % name
    cmd("l2", "ping 192.168.1.1 > %s/ping.txt &" % dir)
    c = "mkdir -p %s; iperf -c 192.168.1.1 -t %s -i 1 -Z reno > %s/iperf.txt" % (dir, t, dir)
    progress(5)
    cmd("l2", "modprobe tcp_probe; cat /proc/net/tcpprobe > %s/tcp_probe.txt" % dir)
    cmd("l2", c)
    cmd("l3", c)

def finishexpt(name):
    for h in hosts.keys():
        cmd(h, "killall -9 iperf ping cat; rmmod tcp_probe", True)
    cmd("alonzo", "killall -9 perl minicom", True)
    cmd("l2", "tc qdisc del dev eth1 root")
    cmd("l3", "tc qdisc del dev eth0 root")
    Popen("scp alonzo:~/q-%s.txt ." % (name), shell=True).wait()

def parse_queue_size(name):
    pat = re.compile(r'Q_TOTAL_COUNT_CELL=(.*)>')
    ret = []
    lines = open("./q-%s.txt" % name).read().strip().split('\n')
    for l in lines:
        m = pat.search(l)
        if m:
            cells = int(m.group(1), 16)
            ret.append(128 *  cells / 1024.0)
    return ret

def print_qs(lst, file):
    t = 0.0
    f = open(file, "w")
    for l in lst:
        print >>f, '%.3f,%.3f' % (t, l * 1024 / 1500.0)
        t += 0.125
    f.close()

def main():
    t=120
    if 0:
        config_bcom_switch(True, 30*1000)
        monitor_bcom_qlen("l1", "dctcp")
        set_dctcp(True)
        runexpt("dctcp", t)
        progress(t+10)
        finishexpt("dctcp")
        print_qs(parse_queue_size("dctcp"), "q-dctcp-plot.txt")

    if 0:
        config_bcom_switch(False, 650*1024)
        monitor_bcom_qlen("l1", "tcp")
        set_dctcp(False)
        runexpt("tcp", t)
        progress(t+10)
        finishexpt("tcp")
    print_qs(parse_queue_size("tcp"), "q-tcp-plot.txt")

try:
    main()
except Exception, e:
    print T.colored(e, "red")
    Popen("ssh alonzo killall -9 minicom perl", shell=True).wait()
