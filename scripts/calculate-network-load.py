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
    load_factor = float(sys.argv[2])
except IndexError:
    print "usage: ./calculate-network-load.py <trace file>.tr load_factor"
    exit(1)

SIM_TIMESTEP = 1e-6 # each bucket represents 1 microseconds of simulation time
INTERVAL_MAX_RATE = 1440e9 * SIM_TIMESTEP

# Functions for Edge Detection
# credit: http://sam-koblenski.blogspot.com/2015/09/everyday-dsp-for-programmers-edge.html

def ExpAvg(sample, avg, w):
    return w*sample + (1-w)*avg

# EdgeDetect...
# - samples : list of values corresponding to a time series "signal"
# - delta_threshold : detect edges when averages differ by >= this
# - global_threshold : detect edges when g_t - tol <= X <= g_t + tol
def EdgeDetect(samples, delta_threshold, global_threshold, tolerance):
    fastAvg = samples[0]
    slowAvg = samples[0]
    prevDifference = 0
    prevInRange = False
    edges = []

    for timestamp, sample in sorted(samples.items()):
        fastAvg = ExpAvg(sample, fastAvg, 0.25)
        print "f: ", fastAvg
        slowAvg = ExpAvg(sample, slowAvg, 0.0625)
        print "s: ", slowAvg
        difference = abs(fastAvg - slowAvg)
        print "f-s: ", difference

        isEdge = prevDifference < delta_threshold and difference >= delta_threshold
        enterRange = fastAvg + tolerance >= global_threshold 
        exitRange = fastAvg + tolerance < global_threshold 

        if isEdge and (enterRange or (exitRange and prevInRange)):
            edges.append(timestamp)
        prevDifference = difference

        if enterRange and not prevInRange:
            prevInRange = True
        if exitRange and prevInRange:
            prevInRange = False

    return edges

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
moving_window = 20
moving_sum = 0.0
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

    # calculate moving average to find start time and end time bounds
    if interval < moving_window-1:
	moving_sum += load_in_interval[interval]
    else:
	if end_time_bound < 0:
	        moving_sum += load_in_interval[interval]
		moving_sum -= load_in_interval[interval-moving_window]
		if moving_sum/moving_window > load_factor-0.05 and start_time_bound < 0:
			start_time_bound = interval
		if start_time_bound > 0 and moving_sum/moving_window < load_factor-0.05:
			end_time_bound = interval
if end_time_bound < 0:
    end_time_bound = max(load_in_interval.items())

# save the (moving-average) time bounds to file
file_path = filename.split("/")[2].split(".")[0] + "_mv_avg_bounds.txt"
with open(file_path, 'w') as file:
	file.write(str(start_time_bound))
	file.write("\n")
	file.write(str(end_time_bound))

# edge detection method (compare to moving-average)
#delta_load_threshold = 0.025 # higher --> less edges; lower --> more edges
delta_load_threshold = 0.015 # higher --> less edges; lower --> more edges
tolerance = 0.2
edges = EdgeDetect(load_in_interval, delta_load_threshold, load_factor, tolerance)
print "All Edges: ", edges
start_time_bound = long(np.percentile(edges, 15))
end_time_bound = long(np.percentile(edges, 99))

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
