#!/bin/bash

# Plot inter-dequeue time distribution...

# Exit on any failure...
set -e

python link_dequeues.py --files linkdata-10 linkdata-100 linkdata-400 \
    --expected  193.8 193.8 193.8 \
    --labels "20 flows" "200 flows" "800 flows" \
    --title "" --ccdf --log --out inter-dequeue-deviation-ccdf-latest.pdf --percent

