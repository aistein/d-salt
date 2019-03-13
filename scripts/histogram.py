#!/usr/bin/python3

import numpy as np
import csv
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.size'] = 16

try:
    filename = sys.argv[1]
    testname = filename.strip().split('/')[2].split('.')[0]
except IndexError:
    print("usage: ./create-histogram.py <priority file>.prio")
    exit(1)

#filename = "w1_facebook_memcached_g.prio"

with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    #next(reader)
    num_prio = 8
    total_byPriority = []
    priorities = []
    for priority in range(0,num_prio,1) :
        #print("Add range: " + str(priority))
        total_byPriority.append(0)
        priorities.append(priority)
    #print("Setup: " + str(total_byPriority))

    for flow in reader:
        #print("Adding flow: "+ str(flow))
        flowPriorities = flow[1:num_prio+1]
        flowPriorities = list(map(int, flowPriorities))
        #print("Setup: " + str(flowPriorities))
        for priority in range(0,num_prio,1) :
            #print(priority)
            total_byPriority[priority] = total_byPriority[priority] + flowPriorities[priority]
        #print("After adding flow: " + str(total_byPriority))
    #plt.xlim([0, 8])  
    #binBoundaries = np.linspace(0,8,1)
    
    plt.hist(priorities, rwidth=0.5, align='mid', weights=total_byPriority, bins=np.arange(num_prio+1)-0.5)
    #plt.rcParams.update({'font.size': 16})
    #plt.title(testname + ' -- Total: ' + str(sum(total_byPriority)))
    plt.xlabel("Priority Values", fontsize=16)
    plt.ylabel("Cumulative Bytes", fontsize=16)
    plt.tight_layout()
    plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    outfilename = testname + "_prioDist.png"
    plt.savefig(outfilename, dpi=600)
    plt.clf()
    
    
