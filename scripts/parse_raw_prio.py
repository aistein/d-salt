#!/usr/bin/python

import sys
import csv
import math
import numpy as np

try:
    filename = sys.argv[1]
except IndexError:
    print "usage: ./parse_raw_prio.py <path to raw prio file>"

rawprio_ts = []
with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    for row in reader:
        for i in range(1, len(row)-1, 3):
            if float(row[i]) != 0.0:
                rawprio_ts.append( (float(row[i]), long(row[i+1]), long(row[i+2])) )

sorted_rawprios = [tup[0] for tup in sorted(rawprio_ts, key=lambda tup : tup[0])]

#print "Rawprio by Percentile"
#for pct in np.linspace(start=0, stop=100, num=10):
#    print "{}th percentile value = {}".format(pct, np.percentile(sorted_rawprios, pct))

print "Rawprio by Logspace"
# coonsider 20 buckets?
for i,lg in enumerate(np.logspace(np.log10(min(sorted_rawprios)), np.log10(max(sorted_rawprios)), num=10, dtype=float)):
    print "{}th logspace value = {}".format(i, lg)

#print "Rawprio by Linspace"
#for i,ln in enumerate(np.linspace(min(sorted_rawprios), max(sorted_rawprios), num=10, dtype=float)):
#    print "{}th linspace value = {}".format(i, ln)
