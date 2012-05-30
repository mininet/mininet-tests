#!/bin/sh
sudo ./pair_intervals.py --switches --counts 10,10,10 --time 60 -o switches10.out
sudo ./pair_intervals.py --switches --counts 20,20,20 --time 60 -o switches10.out
sudo ./pair_intervals.py --switches --counts 40,40,40 --time 60 -o switches40.out
sudo ./pair_intervals.py --switches --counts 80,80,80 --time 60 -o switches80.out
 
./plot_pair_intervals.py --all switches*.out
