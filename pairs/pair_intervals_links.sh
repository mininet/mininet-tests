#!/bin/sh
sudo ./pair_intervals.py --counts 10,10,10 --time 60 -o links10.out
sudo ./pair_intervals.py --counts 20,20,20 --time 60 -o links20.out
sudo ./pair_intervals.py --counts 40,40,40 --time 60 -o links40.out
sudo ./pair_intervals.py --counts 80,80,80 --time 60 -o links80.out
 
./plot_pair_intervals.py --all links*.out
