#!/bin/bash

python link_dequeues.py --files 100mbps 1gbps \
	--labels "100Mb/s" "1Gb/s" --ccdf --log --expected 120 12 \
	--title "" \
	-o dctcp-100mbps-1gbps-ccdf-latest.pdf

