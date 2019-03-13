#!/usr/bin/python

from __future__ import division
import sys
import os
import math
import numpy as np
from collections import defaultdict
from tabulate import tabulate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
matplotlib.rcParams['font.size'] = 14

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

def parse_time_ns(tm):
    if tm.endswith('ns'):
        return long(tm[:-4])
    raise ValueError(tm)

BOTTLENECK_RATE = 10e9 # 10Gbps
PERCENTILE_CUTOFF = 99
N_BINS = 8 

## FiveTuple
class FiveTuple(object):
    ## class variables
    ## @var sourceAddress 
    #  source address
    ## @var destinationAddress 
    #  destination address
    ## @var protocol 
    #  network protocol
    ## @var sourcePort 
    #  source port
    ## @var destinationPort 
    #  destination port
    ## @var __slots__ 
    #  class variable list
    __slots__ = ['sourceAddress', 'destinationAddress', 'protocol', 'sourcePort', 'destinationPort']
    def __init__(self, el):
        '''The initializer.
        @param self The object pointer.
        @param el The element.
        '''
        self.sourceAddress = el.get('sourceAddress')
        self.destinationAddress = el.get('destinationAddress')
        self.sourcePort = int(el.get('sourcePort'))
        self.destinationPort = int(el.get('destinationPort'))
        self.protocol = int(el.get('protocol'))
        
## Histogram
class Histogram(object):
    ## class variables
    ## @var bins
    #  histogram bins
    ## @var nbins
    #  number of bins
    ## @var number_of_flows
    #  number of flows
    ## @var __slots__
    #  class variable list
    __slots__ = 'bins', 'nbins', 'number_of_flows'
    def __init__(self, el=None):
        ''' The initializer.
        @param self The object pointer.
        @param el The element.
        '''
        self.bins = []
        if el is not None:
            #self.nbins = int(el.get('nBins'))
            for bin in el.findall('bin'):
                self.bins.append( (float(bin.get("start")), float(bin.get("width")), int(bin.get("count"))) )

## Flow
class Flow(object):
    ## class variables
    ## @var flowId
    #  delay ID
    ## @var delayMean
    #  mean delay
    ## @var packetLossRatio
    #  packet loss ratio
    ## @var rxBitrate
    #  receive bit rate
    ## @var txBitrate
    #  transmit bit rate
    ## @var fiveTuple
    #  five tuple
    ## @var packetSizeMean
    #  packet size mean
    ## @var packetCount
    #  number of packets sent
    ## @var probe_stats_unsorted
    #  unsirted probe stats
    ## @var size
    #  size of flow
    ## @var hopCount
    #  hop count
    ## @var flowInterruptionsHistogram
    #  flow histogram
    ## @var rx_duration
    #  receive duration
    ## @var slowdown
    #  ratio of actual to optimal flow duration
    ## @var rawDuration
    #  actual duration of flow
    ## @var optDuration
    #  optimal duration for a flow of this size in our topology
    ## @var start
    #  starting time of flow in seconds
    ## @var finish
    #  finishing time of flow in seconds
    ## @var __slots__
    #  class variable list
    __slots__ = ['flowId', 'delayMean', 'packetLossRatio', 'rxBitrate', 'txBitrate',
                 'fiveTuple', 'packetSizeMean', 'packetCount', 'probe_stats_unsorted', 'size',
                 'hopCount', 'flowInterruptionsHistogram', 'rx_duration', 'slowdown', 'rawDuration',
                 'optDuration', 'start', 'finish']
    def __init__(self, flow_el):
        ''' The initializer.
        @param self The object pointer.
        @param flow_el The element.
        '''
        self.flowId = int(flow_el.get('flowId'))
        rxPackets = long(flow_el.get('rxPackets'))
        txPackets = long(flow_el.get('txPackets'))
        #start = long(flow_el.get('timeFirstTxPacket')[:-4]) * 1.0e-9
        start = long(flow_el.get('timeFirstRxPacket')[:-4]) * 1.0e-9
        finish = long(flow_el.get('timeLastRxPacket')[:-4]) * 1.0e-9
	tx_duration = float(long(flow_el.get('timeLastTxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
        rx_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstRxPacket')[:-4]))*1e-9
	actual_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
        # known NS3 error that Rx time and Tx time can't be reliably compared
	#actual_duration = rx_duration
	flowsize_bits = float(long(flow_el.get('txBytes')))*8.0
	agg_capacity = float(40e9)
	edge_capacity = float(10e9)
	host_proc_delay = 1.5e-6
        h2e_prop_delay = 10e-9  # delay to travel the length of cable (host-to-edge)
        e2a_prop_delay = 100e-9  # delay to travel the length of cable (edge-to-agg)
        processing_delay = 250e-9   # delay for a packet to be processed by the switch software
	#optimal_flow_duration = float(2.0*flowsize_bits/edge_capacity) + float(2.0*flowsize_bits/agg_capacity)
        h2e_delay_component = float(2.0 * (h2e_prop_delay + flowsize_bits/edge_capacity))
        e2a_delay_component = float(2.0 * (e2a_prop_delay + flowsize_bits/agg_capacity))
        optimal_flow_duration = h2e_delay_component + e2a_delay_component

        slowdown_raw = actual_duration / optimal_flow_duration

        self.slowdown = slowdown_raw
        self.rawDuration = actual_duration
        self.optDuration = optimal_flow_duration

        self.start = start
        self.finish = finish

        self.size = long(flow_el.get('txBytes'))
        self.packetCount = rxPackets
        self.rx_duration = rx_duration
        self.probe_stats_unsorted = []
        if rxPackets:
            self.hopCount = float(flow_el.get('timesForwarded')) / rxPackets + 1
        else:
            self.hopCount = -1000
        if rxPackets:
            self.delayMean = float(flow_el.get('delaySum')[:-4]) / rxPackets * 1e-9
            self.packetSizeMean = float(flow_el.get('rxBytes')) / rxPackets
        else:
            self.delayMean = None
            self.packetSizeMean = None
        if rx_duration > 0:
            self.rxBitrate = long(flow_el.get('rxBytes'))*8 / rx_duration
        else:
            self.rxBitrate = None
        if tx_duration > 0:
            self.txBitrate = long(flow_el.get('txBytes'))*8 / tx_duration
        else:
            self.txBitrate = None
        lost = float(flow_el.get('lostPackets'))
        if rxPackets == 0:
            self.packetLossRatio = None
        else:
            self.packetLossRatio = (lost / (rxPackets + lost))

        interrupt_hist_elem = flow_el.find("flowInterruptionsHistogram")
        if interrupt_hist_elem is None:
            self.flowInterruptionsHistogram = None
        else:
            self.flowInterruptionsHistogram = Histogram(interrupt_hist_elem)

## ProbeFlowStats
class ProbeFlowStats(object):
    ## class variables
    ## @var probeId
    #  probe ID
    ## @var packets
    #  network packets
    ## @var bytes
    #  bytes
    ## @var delayFromFirstProbe
    #  delay from first probe
    ## @var __slots__
    #  class variable list
    __slots__ = ['probeId', 'packets', 'bytes', 'delayFromFirstProbe']

## Simulation
class Simulation(object):
    ## class variables
    ## @var flows
    #  list of flows
    ## @var flow_map
    #  metadata associated with each flow
    def __init__(self, simulation_el):
        ''' The initializer.
        @param self The object pointer.
        @param simulation_el The element.
        '''
        self.flows = []
        flow_map = {}
        FlowClassifier_el, = simulation_el.findall("Ipv4FlowClassifier")
        for flow_el in simulation_el.findall("FlowStats/Flow"):
            flow = Flow(flow_el)
            flow_map[flow.flowId] = flow
            self.flows.append(flow)
        for flow_cls in FlowClassifier_el.findall("Flow"):
            flowId = int(flow_cls.get('flowId'))
            flow_map[flowId].fiveTuple = FiveTuple(flow_cls)

        for probe_elem in simulation_el.findall("FlowProbes/FlowProbe"):
            probeId = int(probe_elem.get('index'))
            for stats in probe_elem.findall("FlowStats"):
                flowId = int(stats.get('flowId'))
                s = ProbeFlowStats()
                s.packets = int(stats.get('packets'))
                s.bytes = long(stats.get('bytes'))
                s.probeId = probeId
                if s.packets > 0:
                    s.delayFromFirstProbe =  parse_time_ns(stats.get('delayFromFirstProbeSum')) / float(s.packets)
                else:
                    s.delayFromFirstProbe = 0
                flow_map[flowId].probe_stats_unsorted.append(s)


def main(argv):

    sim_list = []
    sim_names = []
    sim_profiles = []
    sim_timebounds = [] # in microseconds
    for i, xmlfile in enumerate(argv[1:]):
        file_obj = open(xmlfile)
        raw_simname = xmlfile.split("/")[2].split(".")[0].split("_")
        sim_profile = raw_simname[0]
        sim_profiles.append(int(sim_profile[1]))
        sim_tag = "_".join(raw_simname[1:])
        sim_names.append(sim_tag)
        #sim_names.append("_".join(xmlfile.split("/")[2].split(".")[0].split("_")[1:]))
        print "_".join(raw_simname)
        print "Reading Timebounds file"
        timebounds_file = "_".join(raw_simname) + "_timebounds.txt"
        with open(timebounds_file, 'r') as tbf:
            sim_timebounds.append( ( long(tbf.readline().strip()), long(tbf.readline().strip()) ) )
        print "Reading XML file"
 
        sys.stdout.flush()        
        level = 0
        for event, elem in ElementTree.iterparse(file_obj, events=("start", "end")):
            if event == "start":
                level += 1
            if event == "end":
                level -= 1
                if level == 0 and elem.tag == 'FlowMonitor':
                    sim = Simulation(elem)
                    sim_list.append(sim)
                    elem.clear() # won't need this any more
                    sys.stdout.write(".")
                    sys.stdout.flush()
        print " done."

    colors = ['tab:gray', 'tab:blue', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:orange', 'tab:olive', 'tab:cyan']
    markers = ["x", "o", "v", "s", "+", "x", "d", "1", "2", "3", "4"]

    # replace 'a's with greek 'alpha's
    for i, sim_name in enumerate(sim_names):
        if sim_name[0] == 'a':
            sim_names[i] = r'$\alpha$' + ' = ' + sim_name[1:]

    # 99-Percentile
    fig, ax = plt.subplots()
    plt.yticks(rotation=45)
    offset = 0.0
    for i, sim in enumerate(sim_list):
        flows_of_interest = []
        flowsizes = []
        workload = sim_profiles[i]

	# DO NOT INCLUDE ACKs, Constrain Simulation Time to Steady-State Utilization Periods
        min_time = sim_timebounds[i][0]
        max_time = sim_timebounds[i][1]
        errant_flow_count = 0
        negative_flow_count = 0
        microseconds = lambda t: t * 1.0e6
        for flow in sim.flows:
            if flow.rawDuration < 0:
                negative_flow_count += 1
                continue
            if flow.rawDuration < flow.optDuration:
                #print "-E- measured duration {} < theoretically optimal duration {}".format(
                #        flow.rawDuration, flow.optDuration)
                #print "\t-I- packets sent in errant flow {}".format(flow.packetCount)
                errant_flow_count += 1
                #continue
            if microseconds(flow.start) >= min_time and microseconds(flow.finish) <= max_time:
                if flow.fiveTuple.sourcePort != 9:
                    flows_of_interest.append( flow )

        print "foi len = ", len(flows_of_interest)
        print "super-optimal flows (counted) = ", errant_flow_count
        print "negative flows (not counted) = ", negative_flow_count
        # Break down CT by buckets
        flowsizes = []
        for flow in flows_of_interest:
            flowsizes.append(long(flow.size))
        print "fss len = ", len(flowsizes)
        # 10 logspace buckets by flowsize
        print "max fs = ", max(flowsizes)
        print "min fs = ", min(flowsizes)
        buckets = np.logspace(np.log10(min(flowsizes)), np.log10(max(flowsizes)), num=11, base=10, dtype=long)
        print "buckets = ", buckets[:-2]
        # Buckets of Completion Time organized by Size
        completion_by_bucket = defaultdict(list)
        for flow in flows_of_interest:
            found = False
            for fsize in buckets[:-2]:
                if flow.size <= fsize:
                    completion_by_bucket[fsize].append(flow.rawDuration)
                    found = True
                    break
            if not found:
                fsize = buckets[-2]
                completion_by_bucket[fsize].append(flow.rawDuration)
        # 99th Percentile FCT for each Bucket
        fcts_99p = defaultdict(float)
        for fsize, fcts in completion_by_bucket.items():
            if len(fcts) >= 10:
                fcts_99p[fsize] = np.percentile(sorted(fcts), 99) 
            else:
                print "-E- not enough samples in bucket {}".format(fsize)

	#flowSizes99 = [fsize/8.0 for fsize,_ in sorted(fcts_99p.items())]
	flowSizes99 = [fsize for fsize,_ in sorted(fcts_99p.items())]
        print "flowSizes_99: ", flowSizes99
        flowDuration99 = [fct * 1e6 for _,fct in sorted(fcts_99p.items())] # to microseconds
        print "flowDuration99: ", flowDuration99
        offset += 0.02
        plt.plot(flowSizes99, flowDuration99, colors[i], linestyle='-', marker=markers[i], markevery=0.1+offset,
                label=sim_names[i], markersize=10, linewidth='2')

    #plt.rcParams.update({'font.size': 16})
    #plt.title(argv[1].split("/")[2].split(".")[0].split("_")[0] + " - Flow Size vs. 99% Flow Completion Time")
    plt.xlabel("Flow Size (bytes)", fontsize=16)
    plt.ylabel("Completion Time (us)", fontsize=16)
    #ax.yaxis.set_minor_formatter(ticker.LogFormatter(labelOnlyBase=False))
    #ax.yaxis.set_major_formatter(ticker.LogFormatter(labelOnlyBase=False))
    plt.yscale('log')
    plt.xscale('log')
    plt.legend()
    outfilename = argv[1].split("/")[2].split(".")[0].split("_")[0] + "_fct_99p_all.png"
    plt.grid(True, which="both")
    plt.tight_layout()
    plt.savefig(outfilename, dpi=600)
    plt.clf()

if __name__ == '__main__':
    main(sys.argv)
