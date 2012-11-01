#!/usr/bin/env python
import sys
if len(sys.argv) != 2:
	raise Exception("please provide one arg, the BW in Mbps")
max_pkt_size=1514
sec_to_us=1e6
time=1.0 / (float(sys.argv[1]) * 1e6) * sec_to_us * max_pkt_size * 8
print time

