#!/usr/bin/python

# To calculate the overall network load, we take the total egress from each switch in the network divided by the capacity of the link connected to that switch, and sum all the loads together (never >1 due to flow conservation)

import sys
import csv
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pylab as plt

try:
    filename = sys.argv[1]
except IndexError:
    print "usage: ./calculate-network-load.py <trace file>.tr"
    exit(1)

SIM_TIMESTEP = 1e-6 # each bucket represents 1 microsecond of simulation time
INTERVAL_MAX_RATE = 1440e3
#INTERVAL_MAX_RATE = 3*1440e3 

# gather total bits sent during each nanosecond
egress_bits_in_interval = defaultdict(long)
with open(filename, 'r') as f:
    for line in f:
        raw_trace = line.strip().split(" ")
        if raw_trace[0] == '-':
            interval = long(float(raw_trace[1]) * (1 / SIM_TIMESTEP)) # the "time-interval" this sample falls into
            bitsinsample = long(raw_trace[raw_trace.index("length:") + 1]) * 8
            egress_bits_in_interval[interval] += bitsinsample

# sum up the the loads over all nanoseconds 
load_sum = 0.0
exceeded_cnt = 0
load_in_interval = defaultdict(float)
for interval, bits in sorted(egress_bits_in_interval.iteritems()):
    print "egress_bits_in_interval[", interval, "] = ", egress_bits_in_interval[interval]
    print "load_on_interval[", interval, "] = ", egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    if egress_bits_in_interval[interval] > INTERVAL_MAX_RATE:
        exceeded_cnt += 1
        load_in_interval[interval] = 1.0;
    else:
        load_in_interval[interval] = egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    load_sum += load_in_interval[interval]

# calculate the average over all nanoseconds (for which we have measurements)
print "Number of Times Limit Exceeded: ", exceeded_cnt
print "Number of Intervals: ", len(egress_bits_in_interval)
print "Average Network Load: ", load_sum * 100 / len(egress_bits_in_interval), " %"
print "Max Network Load: ", max(load_in_interval.values()) * 100, " %"

# plot time series of utilizations
load_in_interval.update((x, y*100) for x, y in load_in_interval.items())
lists = sorted(load_in_interval.items()) # sorted by key, return a list of tuples
print lists
x, y = zip(*lists) # unpack a list of pairs into two tuples
plt.plot(x, y)
plt.title("time series utilization")
plt.xlabel("Time stamp (us)")
plt.ylabel("Network % utilization")
outfilename = filename.split("/")[2].split(".")[0] + "_util.png"
plt.savefig(outfilename)
