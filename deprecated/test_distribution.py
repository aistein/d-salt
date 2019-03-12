#!/usr/bin/python3

import sys
from collections import defaultdict

try:
    sample_file = sys.argv[1]
    buckets = int(sys.argv[2])
except IndexError:
    print("usage: ./test_distributions.py <sample_file> <num_buckets>")

f = open(sample_file)
x = []
for line in f:
    x.append(float(line.strip()))
max = x[0]
for v in x:
    if v > max:
        max = v
bucketsize = max / buckets
k = 1
bins = defaultdict(list)
x.sort()
for v in x:
    if v > k * bucketsize:
        k += 1
    bins[k * bucketsize].append(v)
for k in bins.keys():
    print("Bin {: >20} has {: >20}".format(k,len(bins[k])))
