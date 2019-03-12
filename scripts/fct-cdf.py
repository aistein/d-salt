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
import matplotlib.patches as patches
from scipy.stats import norm
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree

def parse_time_ns(tm):
    if tm.endswith('ns'):
        return long(tm[:-4])
    raise ValueError(tm)

BOTTLENECK_RATE = 10e9 # 10Gbps
#BOTTLENECK_RATE = 10e6 # 10Mbps
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
    ## @var start
    #  starting time of flow in seconds
    ## @var finish
    #  finishing time of flow in seconds
    ## @var __slots__
    #  class variable list
    __slots__ = ['flowId', 'delayMean', 'packetLossRatio', 'rxBitrate', 'txBitrate',
                 'fiveTuple', 'packetSizeMean', 'probe_stats_unsorted', 'size',
                 'hopCount', 'flowInterruptionsHistogram', 'rx_duration', 'slowdown', 'rawDuration',
                 'start', 'finish']
    def __init__(self, flow_el):
        ''' The initializer.
        @param self The object pointer.
        @param flow_el The element.
        '''
        self.flowId = int(flow_el.get('flowId'))
        rxPackets = long(flow_el.get('rxPackets'))
        txPackets = long(flow_el.get('txPackets'))
        start = long(flow_el.get('timeFirstTxPacket')[:-4]) * 1.0e-9
        finish = long(flow_el.get('timeLastRxPacket')[:-4]) * 1.0e-9
	tx_duration = float(long(flow_el.get('timeLastTxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
        rx_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstRxPacket')[:-4]))*1e-9
	actual_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
	flowsize_bits = float(long(flow_el.get('txBytes')))*8.0
	agg_capacity = float(40e9)
	edge_capacity = float(10e9)
	host_proc_delay = 1.5e-6
        prop_delay = 2e-6  # delay to travel the length of cable
        processing_delay = 250e-9   # delay for a packet to be processed by the switch software
	optimal_flow_duration = float(2.0*flowsize_bits/edge_capacity) + float(2.0*flowsize_bits/agg_capacity)
        log_base = 10
        slowdown_raw = actual_duration / optimal_flow_duration

        self.slowdown = slowdown_raw
        self.rawDuration = actual_duration

        self.start = start
        self.finish = finish

        self.size = long(flow_el.get('txBytes'))
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


# Function to Fix Step and the end of CDFs
# StackOverflow Credit: https://stackoverflow.com/a/52921726/3341596
def fix_hist_step_vertical_line_at_end(ax):
    axpolygons = [poly for poly in ax.get_children() if isinstance(poly, patches.Polygon)]
    for poly in axpolygons:
                poly.set_xy(poly.get_xy()[:-1])

def main(argv):

    sim_list = []
    sim_names = []
    sim_timebounds = [] # in microseconds
    for i, xmlfile in enumerate(argv[1:]):
        file_obj = open(xmlfile)
        raw_simname = xmlfile.split("/")[2].split(".")[0].split("_")
        sim_profile = raw_simname[0]
        sim_tag = "_".join(raw_simname[1:])
        sim_names.append(sim_tag)
        #sim_names.append("_".join(xmlfile.split("/")[2].split(".")[0].split("_")[1:]))
        print "_".join(raw_simname)
        print "Reading Timebounds File"
        timebounds_file = "_".join(raw_simname) + "_timebounds.txt"
        with open(timebounds_file, 'r') as tbf:
            sim_timebounds.append( ( long(tbf.readline().strip()), long(tbf.readline().strip()) ) )
        print "Reading XML file \n",
 
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
    markers = ["x", "o", "v", "s"]

    # replace 'a's with greek 'alpha's
    for i, sim_name in enumerate(sim_names):
        if sim_name[0] == 'a':
            sim_names[i] = r'$\alpha$' + ' = ' + sim_name[1:] 

    # FCT CDF
    fig, ax = plt.subplots()
    offset = 0.0
    for i, sim in enumerate(sim_list):
        flows_of_interest = []
        flowsizes = []

	# DO NOT INCLUDE ACKs
        min_time = sim_timebounds[i][0]
        print min_time
        max_time = sim_timebounds[i][1]
        print max_time
        microseconds = lambda t: t * 1.0e6
        for flow in sim.flows:
            if microseconds(flow.start) >= min_time and microseconds(flow.finish) <= max_time:
                if flow.fiveTuple.sourcePort != 9:
                    flows_of_interest.append( flow )

        # Break down CT by buckets
        fcts = []
        for flow in flows_of_interest:
            if flow.rawDuration > 0:
                fcts.append(float(flow.rawDuration))

        nbins = 1000
        #mu = np.mean(fcts)
        #sigma = np.std(fcts)
        x = np.logspace(np.log10(min(fcts)), np.log10(max(fcts)), num=nbins, dtype=float)
        #y = norm.cdf(x, mu, sigma)

        offset += 0.02
        cdf,bins,_ = plt.hist(fcts, bins=x, density=True, alpha=0.5, color=colors[i], linestyle='-', histtype='step', cumulative=True, label=None)
        plt.plot(bins[:-1], cdf, linestyle=None, label=sim_names[i], color=colors[i], marker=markers[i], markevery=0.1+offset)
        #plt.plot(x, y, color=colors[i], linestyle='--', alpha=0.5, label=sim_names[i]+'_norm')

    plt.title(argv[1].split("/")[2].split(".")[0].split("_")[0] + " - Flow Completion Time CDF")
    plt.ylabel("Proportion of Flows")
    plt.xlabel("Flow Completion Time (s)")
    plt.xscale('log')
    plt.ylim(0.0,1.0)
    plt.legend()
    fix_hist_step_vertical_line_at_end(ax)
    outfilename = argv[1].split("/")[2].split(".")[0].split("_")[0] + "_fct_cdf.png"
    plt.tight_layout()
    plt.savefig(outfilename)
    plt.clf()

if __name__ == '__main__':
    main(sys.argv)
