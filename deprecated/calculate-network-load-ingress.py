#!/usr/bin/python

# To calculate the overall network load, we take the total egress from each
# ... switch in the network divided by the capacity of the link connected
# ... to that switch, and sum all the loads together (never >1 due to flow
# ... conservation)

import sys
import csv
from collections import defaultdict

try:
    filename = sys.argv[1]
except IndexError:
    print "usage: ./calculate-network-load.py <flowrate-by-switch file-path>"
    exit(1)

# How To Calculate Unit Network Load?
# - If a network consisted of two endpoints connected by a single 10Gbps link...
# - then the maximum amount of flow possible is 10Gbps.  Now, let say in the 1s of
# - measurements collected, each endpoint's egress bits summed up to 5Gb.  Then
# - the total network load over that 1s interval is 5Gbps / 10Gbps = 50%.
#
# - Now, what if we have two endpoints connected via a single router, and one of
# - the links is a bottleneck - say 5Gpbs? Now the maximum rate is limited by the
# - bottleneck, and the total network load is 5Gbps / 5Gbps = 100%.
#
# - By the "max-flow = min-cut" theorem, we find that the max-flow possible in our
# - network topology is 1440 Gbps.  If we wish to re-cast this to be relevant for 
# - measurements collected in a single 1-nanosecond timestep, we must change the
# - max-flow to (1440e9 bits / s) * (1e-9 s / us) = 1440 bits / ns.  
#
# - Now, to get the total network utilization for that timestep, we simply need to 
# - take all the egress-bits sent from any host (excluding routers) in
# - the network during that time, and divide by the timestep-max-flow:
#
#       Utilization over interval I = Total Bits Sent over I / Max-Rate over I 
#
SIM_TIMESTEP = 1e-9 # each bucket represents 1 nanosecond of simulation time
INTERVAL_MAX_RATE = 1440

# gather total bits sent during each nanosecond
egress_bits_in_interval = defaultdict(int)
with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    next(reader)
    for row in reader:
        interval = row[0] # the "time-interval" this sample falls into
        bitsinsample = int(row[1]) * 8
        egress_bits_in_interval[interval] += bitsinsample

# sum up the the loads over all nanoseconds 
load_sum = 0.0
exceeded_cnt = 0
load_in_interval = defaultdict(float)
for interval, bits in egress_bits_in_interval.iteritems():
    print "egress_bits_in_interval[", interval, "] = ", egress_bits_in_interval[interval]
    print "load_on_interval[", interval, "] = ", egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    if egress_bits_in_interval[interval] > 1440:
        exceeded_cnt += 1
        load_in_interval[interval] = 1.0;
    else:
        load_in_interval[interval] = egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    load_sum += load_in_interval[interval]

# calculate the average over all nanoseconds (for which we have measurements)
print "Number of Intervals: ", len(egress_bits_in_interval)
print "Average Network Load: ", load_sum * 100 / len(egress_bits_in_interval), " %"
print "Max Network Load: ", max(load_in_interval.values()) * 100, " %"
