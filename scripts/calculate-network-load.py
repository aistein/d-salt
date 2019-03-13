#!/usr/bin/python

# To calculate the overall network load, we take the total egress from each switch in the network divided by the capacity of the link connected to that switch, and sum all the loads together (never >1 due to flow conservation)

import sys
import csv
import re
import numpy as np
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pylab as plt

try:
    filename = sys.argv[1]
    desired_load = float(sys.argv[2])
    if desired_load > 1.0:
        print "required: desired_load <= 1.0"
        exit(1)
except IndexError:
    print "usage: ./calculate-network-load.py <trace file>.tr <desired_load>"
    exit(1)

SIM_TIMESTEP = 1e-6 # each bucket represents 1 microseconds of simulation time
INTERVAL_MAX_RATE = 1440e9 * SIM_TIMESTEP

# Functions for Edge Detection
# credit: http://sam-koblenski.blogspot.com/2015/09/everyday-dsp-for-programmers-edge.html

def ExpAvg(sample, avg, w):
    return w*sample + (1-w)*avg

def EdgeDetect(samples, global_threshold, tolerance):
    """Determine the time-bounds when load is in the desired range.

    Keyword arguments:
    samples -- sorted load values representing the signal on which we wish to detect edges
    global_threshold -- the exact desired network load
    tolerance -- amount below desired load it is okay to start detecting edges
    """
    avg = samples[0]
    firstEdge = lastEdge = -1L

    for timestamp, sample in sorted(samples.items()):
        EXP_AVG_SPEED = 0.50
        avg = ExpAvg(sample, avg, EXP_AVG_SPEED)
        if avg + tolerance >= global_threshold:
            if firstEdge == -1L:
                firstEdge = timestamp
            else:
                lastEdge = timestamp

    return firstEdge, lastEdge

# gather total bits sent during each nanosecond
egress_bits_in_interval = defaultdict(long)
packet_size_avg = 0
num_packets = 0
max_interval = -1

with open(filename, 'r') as f:
    for line in f:
        raw_trace = line.strip().split(" ")
        operation = raw_trace[0]
        source_port = int(raw_trace[raw_trace.index("ns3::TcpHeader") + 1][1:])
        packet_size = long(raw_trace[raw_trace.index("length:") + 1])
        if operation == '-':
            packet_size_avg += packet_size
            num_packets += 1
            interval = long(float(raw_trace[1]) * (1 / SIM_TIMESTEP)) # the "time-interval" this sample falls into
            if max_interval < interval:
		max_interval = interval
	    bitsinsample = packet_size * 8
            egress_bits_in_interval[interval] += bitsinsample 
    # populate other intervals with 0 bytes sent
    for i in range(0, max_interval+1):
	if i not in egress_bits_in_interval:
		egress_bits_in_interval[interval] = 0

# sum up the the loads over all nanoseconds 
load_sum = 0.0
exceeded_cnt = 0
load_in_interval = defaultdict(float)
start_time_bound = -1
end_time_bound = -1
for interval, bits in sorted(egress_bits_in_interval.iteritems()):
    #print "egress_bits_in_interval[", interval, "] = ", egress_bits_in_interval[interval]
    #print "load_on_interval[", interval, "] = ", egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    if egress_bits_in_interval[interval] > INTERVAL_MAX_RATE:
        exceeded_cnt += 1
        load_in_interval[interval] = 1.0;
    else:
        load_in_interval[interval] = egress_bits_in_interval[interval] * 1.0 / INTERVAL_MAX_RATE
    load_sum += load_in_interval[interval]

# edge detection to determine time interval of desired load
tolerance = 0.1
start_time_bound, end_time_bound = EdgeDetect(load_in_interval, desired_load, tolerance)

# save the (edge-detection) time bounds to file
file_path = filename.split("/")[2].split(".")[0] + "_timebounds.txt"
with open(file_path, 'w') as file:
	file.write(str(start_time_bound))
	file.write("\n")
	file.write(str(end_time_bound))

# calculate the average over all intervals/buckets (for which we have measurements)
print "Number of Times Limit Exceeded: ", exceeded_cnt
print "Number of Intervals: ", len(egress_bits_in_interval)
print "Average Network Load: ", load_sum * 100 / len(egress_bits_in_interval), " %"
print "Max Network Load: ", max(load_in_interval.values()) * 100, " %"

# plot time series of utilizations
load_in_interval.update((x, y*100) for x, y in load_in_interval.items())
lists = sorted(load_in_interval.items()) # sorted by key, return a list of tuples
x, y = zip(*lists) # unpack a list of pairs into two tuples
plt.plot(x, y)
plt.title("time series utilization")
plt.xlabel("Time stamp (us)")
plt.ylabel("Network % utilization")
outfilename = filename.split("/")[2].split(".")[0] + "_util.png"
plt.savefig(outfilename)
