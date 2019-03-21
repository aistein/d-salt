#!/usr/bin/python3

import numpy as np
import csv
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.size'] = 16
matplotlib.rcParams['xtick.labelsize'] = 14
matplotlib.rcParams['ytick.labelsize'] = 14

try:
    name1 = str(sys.argv[1])
    file1 = str(sys.argv[2])
    name2 = str(sys.argv[3])
    file2 = str(sys.argv[4])
    title = str(sys.argv[5])
except:
    exit("usage: ./prio_dist_pair.py <test1 name> <test1 file>.prio <test2 name> <test2 file>.prio <title>")

with open(file1, 'r') as f1, open(file2, 'r') as f2:
    r1 = csv.reader(f1, delimiter=',')
    r2 = csv.reader(f2, delimiter=',')
    num_prio = 8

    def tally(fd, lst):
        for flowentry in fd:
            flowid = flowentry[0]
            for b, bintotal in enumerate(flowentry[1:]):
                try:
                    lst[b] += int(bintotal)
                except IndexError:
                    pass

    t1_priorities = [0 for _ in range(num_prio)]
    t2_priorities = [0 for _ in range(num_prio)]
    tally(r1, t1_priorities)
    tally(r2, t2_priorities)
    print(t1_priorities)
    print(t2_priorities)
    
    index = np.arange(num_prio)
    bar_width = 0.35
    use_log = True
    plt.bar(index, t1_priorities, bar_width, color='tab:blue', label=name1, log=use_log)
    plt.bar(index + bar_width, t2_priorities, bar_width, color='tab:green', label=name2, log=use_log)
    plt.xlabel("Priority Values", fontsize=16)
    plt.ylabel("Cumulative Bytes", fontsize=16)
    plt.xticks([k for k in range(0,8)], ('0(Hi)', '1', '2', '3', '4', '5', '6', '7(Lo)'), rotation=20)
    plt.legend()
    plt.tight_layout()
    outfilename = "_".join([title, "prioDist.png"])
    plt.savefig(outfilename, dpi=600)
    plt.clf()
    
    
