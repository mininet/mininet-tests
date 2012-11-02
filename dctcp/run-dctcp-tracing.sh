#!/bin/bash

#bws="10 100 1000"
bws="10 20 40 80 160 320 640 1280"
#bws="1280"
t=20
n=3
maxq=425

source ../tracing/trace.sh
exptid=`date +%b%d-%H:%M`

if [ "$UID" != "0" ]; then
    warn "Please run as root"
    exit 0
fi

echo "Setting to one core:"
../tracing/example/mod-cores.sh 1

finish() {
    # Re-enable all cores
    # TEMP
    #../tracing/example/mod-cores.sh

    # Clean up
    killall -9 python iperf
    mn -c

    exit
}

clean_text_files () {
    # Remove random output character in the text file
    dir=${1:-/tmp}
    pushd $dir
    mkdir -p clean
    for f in *.txt; do
        echo "Cleaning $f"
        cat $f | tr -d '\001' > clean/$f
    done
    popd
}

trap finish SIGINT

function tcp {
	bw=$1
	odir=tcp-n$n-bw$bw
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n
	sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	sudo python ../util/plot_queue.py -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
	sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function ecn {
	bw=$1
	odir=tcpecn-n$n-bw$bw
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --ecn
	sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	sudo python ../util/plot_queue.py -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
	sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

function dctcp {
    bw=$1
    odir=dctcp-n$n-bw$bw
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --dctcp
	sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	sudo python ../util/plot_queue.py --maxy 50 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
	sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png
}

# Compile module, insert mntracer, etc.
trace_init

for bw in $bws; do
#for expt in tcp dctcp; do  # ecn was here, but commented out.
#for expt in tcp; do
    expt="dctcp"
	#dir=$exptid/bw$bw-n$n-proto$proto-P$P-cpu$cpu
	#dir=$exptid/tcp-n$n-bw$bw
    dir=$expt-n$n-bw$bw
    mkdir -p $dir
    odir=$expt-n$n-bw$bw

    # Start the experiment
	trace_start $dir/mntrace
	# TCP only for now.
    if [ "$expt" == "tcp" ]; then 
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n
    elif [ "$expt" == "ecn" ]; then
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --ecn
    elif [ "$expt" == "dctcp" ]; then
	sudo python dctcp.py --bw $bw --maxq $maxq --dir $odir -t $t -n $n --dctcp
    fi

	trace_stop $dir/mntrace
	grep mn_ $dir/mntrace > $dir/mntrace_trimmed

    # Run plotting scripts
	sudo python ../util/plot_rate.py --maxy $bw -f $odir/txrate.txt -o $odir/rate.png
	sudo python ../util/plot_queue.py --maxy 50 -f $odir/qlen_s1-eth1.txt -o $odir/qlen.png
	sudo python ../util/plot_tcpprobe.py -f $odir/tcp_probe.txt -o $odir/cwnd.png

    #clean_text_files $dir

    trace_plot $dir/mntrace

    wait

done

#done

finish


