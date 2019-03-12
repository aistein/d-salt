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
    #  ratio of actual to optimal flow duration
    ## @var __slots__
    #  class variable list
    __slots__ = ['flowId', 'delayMean', 'packetLossRatio', 'rxBitrate', 'txBitrate',
                 'fiveTuple', 'packetSizeMean', 'probe_stats_unsorted', 'size',
                 'hopCount', 'flowInterruptionsHistogram', 'rx_duration', 'slowdown', 'rawDuration']
    def __init__(self, flow_el):
        ''' The initializer.
        @param self The object pointer.
        @param flow_el The element.
        '''
        self.flowId = int(flow_el.get('flowId'))
        rxPackets = long(flow_el.get('rxPackets'))
        txPackets = long(flow_el.get('txPackets'))
        #print "TxPackets: " + str(txPackets) + "\n"
	tx_duration = float(long(flow_el.get('timeLastTxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
        rx_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstRxPacket')[:-4]))*1e-9
	actual_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstTxPacket')[:-4]))*1e-9
        #actual_duration = float(long(flow_el.get('timeLastRxPacket')[:-4]) - long(flow_el.get('timeFirstRxPacket')[:-4]))*1e-9
        #print "Actual Duration: ", actual_duration
        #optimal_flow_duration = float(long(flow_el.get('txBytes'))*8.0 / BOTTLENECK_RATE)
	#flowsize_bits = float((long(flow_el.get('rxBytes')) + long(flow_el.get('txBytes')))*8.0)
	flowsize_bits = float(long(flow_el.get('txBytes')))*8.0
	agg_capacity = float(40e9)
	edge_capacity = float(10e9)
	host_proc_delay = 1.5e-6
        #prop_delay = 250e-3
        prop_delay = 2e-6  # delay to travel the length of cable
        processing_delay = 250e-9   # delay for a packet to be processed by the switch software
	optimal_flow_duration = float(2.0*flowsize_bits/edge_capacity) + float(2.0*flowsize_bits/agg_capacity)
	#optimal_flow_duration = (2.0*flowsize_bits/edge_capacity) + (2.0*flowsize_bits/agg_capacity) + txPackets*(4.0*prop_delay)
	#optimal_flow_duration = (2.0*flowsize_bits/edge_capacity) + (2.0*flowsize_bits/agg_capacity) + txPackets*(3*processing_delay) + rxPackets*host_proc_delay
	#print "Optimal Duration: ", 
	print "Optimal Duration: " + str(optimal_flow_duration) + "\t actual_duration: " + str(actual_duration) + "\t flowID: " + str(self.flowId) + "\n"
        log_base = 10
        #slowdown_raw = rx_duration / optimal_flow_duration
        slowdown_raw = actual_duration / optimal_flow_duration
	#if slowdown_raw < 1:
	#	slowdown_raw = -1
        #if slowdown_raw >= log_base:
        #    self.slowdown = math.log( slowdown_raw, log_base )
        #else:
        #    self.slowdown = 1
        self.slowdown = slowdown_raw
        self.rawDuration = actual_duration

        #slowdown = self.slowdown
        self.size = long(flow_el.get('txBytes'))
        #print "Size: ", long(flow_el.get('txBytes')), "  Slowdown: ", slowdown
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
        #print "rxBytes: %s; txPackets: %s; rxPackets: %s; lostPackets: %s" % (flow_el.get('rxBytes'), txPackets, rxPackets, lost)
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
    file_obj = open(argv[1])
    print "Reading XML file \n",
 
    sys.stdout.flush()        
    level = 0
    sim_list = []
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


    for sim in sim_list:
        flows_of_interest = []
        flowsizes = []
        buckets = []

	# DO NOT INCLUDE ACKs
        for flow in sim.flows:
            if flow.fiveTuple.sourcePort != 9 and flow.size != 336:
                flows_of_interest.append( flow )


        print "average duration: ", np.mean([flow.rawDuration for flow in flows_of_interest if flow.rawDuration >= 0])
        print "total number of flows: ", len(flows_of_interest)
        for flow in flows_of_interest:
            flowsizes.append(flow.size)
        #flowSizes = [flow.size/8 for flow in flows_of_interest if flow.slowdown >= 0]
        #flowSlowDown = [flow.slowdown for flow in flows_of_interest if flow.slowdown >= 0]
	flowSizes = [flow.size/8 for flow in flows_of_interest]
        flowDuration = [flow.rawDuration for flow in flows_of_interest]
        plt.plot(flowSizes, flowDuration, 'k.')
        plt.title("Flow Size versus Completion Time")
        plt.xlabel("Flow Size (bytes)")
        plt.ylabel("Duration (s)")
	#plt.ylim([0,60])
        plt.yscale('log')
	plt.xscale('log')
	outfilename = argv[1].split("/")[2].split(".")[0] + "_completion_RAW.png"
        plt.tight_layout()
        plt.savefig(outfilename)
        plt.clf()

	# plot 99 percentile duration vs message sizes in bytes
	flowinfo = defaultdict(list)
        num_flows = len(flows_of_interest)
        bucket = []
        duration99 = []
        duration50 = []
        message_sizes = []
        for flow in flows_of_interest:
                size = int(flow.size/8)
		duration = flow.rawDuration
		temp = []
                if size not in flowinfo:
                        flowinfo[size] = [duration]
		else:
	                flowinfo[size].append(duration)
	sorted_flows = sorted(flowinfo.items(), key=lambda s: s[0])
        for k,v in sorted_flows:
                message_sizes.append(k)
                duration99.append(np.percentile(sorted(v), 99))
                duration50.append(np.percentile(sorted(v), 50))
        ax = plt.plot(message_sizes, duration99, 'k.')
        plt.title("99% completion time vs. message sizes")
        plt.xlabel("message sizes (bytes)")
        plt.ylabel("99 percentile completion time (s)")
        plt.xscale('log')
        plt.yscale('log')
	#plt.ylim([0,45])
        #plt.xticks(list(range(0, 100,5))) 
        #plt.xticks('1','2','3','5','11','28','85','167','291','508','1619')
        #plt.xticks([1,2,3,5,11,28,85,167,291,508,1619])
        outfilename = argv[1].split("/")[2].split(".")[0] + "_completion99.png"
        plt.tight_layout()
        plt.savefig(outfilename)                
	plt.clf()
        
	# Plot median completion vs. message sizes	
        ax2 = plt.plot(message_sizes, duration50, 'k.')
        plt.title("Median completion vs. message sizes")
        plt.xlabel("message sizes (bytes)")
        plt.ylabel("Median completion time (s)")
        plt.xscale('log')
        plt.yscale('log')
	#plt.ylim([0,12])
        #plt.xticks(list(range(0, 100,5))) 
        #plt.xticks('1','2','3','5','11','28','85','167','291','508','1619')
        #plt.xticks([1,2,3,5,11,28,85,167,291,508,1619])
        outfilename = argv[1].split("/")[2].split(".")[0] + "_median.png"
        plt.tight_layout()
	plt.savefig(outfilename)		
	plt.clf()	

        # Break down CT by buckets
        buckets = []
        flowsizes = []
        for flow in flows_of_interest:
            flowsizes.append(int(flow.size))
        for k in np.linspace(0, 100, 9):
            buckets.append(int(np.percentile(sorted(flowsizes), k)))
        completion_by_bucket = defaultdict(list)
        for flow in flows_of_interest:
            for bucket in buckets:
                if flow.size <= bucket:
                    completion_by_bucket[bucket].append(flow.rawDuration)
                    break

        sorted_keys = sorted(completion_by_bucket.keys())
        # Print mean/median for short flow Completion time 
        print "Short Flow Mean Completion Time: ", np.mean(completion_by_bucket[sorted_keys[0]])
        print "Short Flow Median Completion Time: ", np.percentile(completion_by_bucket[sorted_keys[0]], 50)

        # Print mean/median for long flow Completion time 
        print "Long Flow Mean Completion Time: ", np.mean(completion_by_bucket[sorted_keys[-1]])
        print "Long Flow Median Completion Time: ", np.percentile(completion_by_bucket[sorted_keys[-1]], 50)

if __name__ == '__main__':
    main(sys.argv)
