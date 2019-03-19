#!/usr/bin/python

import sys
import csv
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    filename = sys.argv[1]
    cutoff_rank = long(sys.argv[2])
except:
    print "usage: ./parse_raw_prio.py <path to raw prio file> <cutoff rank>"

rawprio_ts = []
with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    for row in reader:
        for i in range(1, len(row)-2, 3):
            if float(row[i]) != 0.0:
                rawprio_ts.append( (float(row[i]), long(row[i+1]), long(row[i+2])) )

sorted_rawprios = [tup[0] for tup in sorted(rawprio_ts, key=lambda tup : tup[0])]
print "number of samples = {}".format(len(sorted_rawprios))

#print "Rawprio by Percentile"
#for pct in np.linspace(start=0, stop=100, num=10):
#    print "{}th percentile value = {}".format(pct, np.percentile(sorted_rawprios, pct))
#
#print "Rawprio by Logspace"
## coonsider 20 buckets?
#for i,lg in enumerate(np.logspace(np.log10(min(sorted_rawprios)), np.log10(max(sorted_rawprios)), base=10, num=10, dtype=float)):
#    print "{}th logspace value = {}".format(i, lg)
#
#print "Rawprio by Linspace"
#for i,ln in enumerate(np.linspace(min(sorted_rawprios), max(sorted_rawprios), num=10, dtype=float)):
#    print "{}th linspace value = {}".format(i, ln)

print "8 Evenly Spaced Values from the Ranked RawPrios:"
print "print minprio: ",sorted_rawprios[0]
print "print maxprio: ",sorted_rawprios[-1]
limits = [] 
for k, rp in enumerate(sorted_rawprios):
    if k > cutoff_rank and k % ((len(sorted_rawprios)-cutoff_rank) // 8) == 0:
        limits.append(str(rp))
print "limits = {" + ", ".join(limits[::-1]) + "};"

plt.plot([k for k in range(len(sorted_rawprios))], sorted_rawprios, linestyle='-')
plt.xlabel("Rank")
plt.ylabel("Raw Priority Value")
plt.yscale('log')
plt.savefig(filename.split('/')[-1] + '.png', dpi=600)
