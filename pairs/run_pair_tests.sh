#!/bin/bash

# bare
for links in 10 20 40 80
do
    echo "sudo ./pair_intervals_new.py --counts $links,$links,$links --time 60 -o results/pairs_bare_${links}links.json"
    sudo ./pair_intervals_new.py --counts $links,$links,$links --time 60 -o results/pairs_bare_${links}links.json
done

# cpu isolation only
for links in 10 20 40 80
do
    echo "sudo ./pair_intervals_new.py --counts $links,$links,$links -p --time 60 -o results/pairs_cpu_${links}links.json"
    sudo ./pair_intervals_new.py --counts $links,$links,$links -p --time 60 -o results/pairs_cpu_${links}links.json
done

# bw isolation only
for bw in {100..1000..100}
do
    for links in 10 20 40 80
    do
        echo "sudo ./pair_intervals_new.py --counts $links,$links,$links -b $bw --time 60 -o results/pairs_bw${bw}_${links}links.json"
        sudo ./pair_intervals_new.py --counts $links,$links,$links -b $bw --time 60 -o results/pairs_bw${bw}_${links}links.json
    done
done

# cpu + bw isolation
for bw in {100..1000..100}
do
    for links in 10 20 40 80
    do
        echo "sudo ./pair_intervals_new.py --counts $links,$links,$links -p -b $bw --time 60 -o results/pairs_cpu_bw${bw}_${links}links.json"
        sudo ./pair_intervals_new.py --counts $links,$links,$links -p -b $bw --time 60 -o results/pairs_cpu_bw${bw}_${links}links.json
    done
done

