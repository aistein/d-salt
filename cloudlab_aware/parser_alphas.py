#!/usr/bin/env python3
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.size'] = 16
matplotlib.rcParams['xtick.labelsize'] = 14
matplotlib.rcParams['ytick.labelsize'] = 14
matplotlib.rcParams['legend.facecolor'] = 'white'
matplotlib.rcParams['legend.framealpha'] = 1
from scipy.stats import norm
import sys
import os
import numpy as np
from collections import defaultdict
import matplotlib.patches as patches

# USAGE
print("USAGE: ./parser_alphas.py <outfilename_prefix: w5> <distFile name>")  

# CONFIGURATION
distFile = sys.argv[2]
outfilename_prefix = 'cloudlab_aware_' + sys.argv[1]
path = data_directory = "cloudlab_aware"

colors = ['tab:gray','tab:green', 'tab:blue','tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:orange', 'tab:olive', 'tab:cyan']
markers = ["x", "v", "o", "s", "+", "x", "d", "1", "2", "3", "4"]


def readFolder(folder, alpha):
        print('in folder',folder)
        print("Alpha = ",alpha)
        flows=[]
        pkts=[]
        for i in range(1,17):
                #print('%s/node%d/receiver.log'%(folder,i))
                with open('%s/node%d/receiver.log'%(folder,i) ) as f:
                        for l in f:
                                try:
                                        w = l.split()
                                        item = (w[1], int(w[2]), int(w[3])) #flow_start_time, flow_size, completion_time_nano
                                        if int(w[2]) > 0:
                                                flows.append(item)
                                except:
                                        w = l.split()
                                        firsttime = w[1]
                                        pass
        return flows

flows_pbs = {}
for (dirpath, dirnames, filenames) in os.walk(path):
	print(dirnames)
	for dir in dirnames:
		alpha = float(dir.split('_')[2])
		folder = data_directory + '/' +  dir + '/' + distFile + '/' + 'pbs'
		flows_pbs[alpha] = readFolder(folder, alpha)
	break

offset = 0
percentile = [25,50,75,90,99]
results = {}
#DSALT FCT plot vary alpha on x-axis
for key in sorted(flows_pbs):
	# populate all FCTs for the alpha
	fcts = [flow[2]*1e-9 for flow in flows_pbs[key]] # convert times into seconds
	#print(fcts)
	# find percentiles
	for percent in percentile:
		values = []
		if percent not in results:
			results[percent] = values
		values = results[percent]
		values.append(np.percentile(sorted(fcts), percent))
		results[percent] = values

# plot all percentiles on y-axis and vary alpha on x-axis
xaxis = sorted(flows_pbs, key=flows_pbs.get)
print(xaxis)
for i in range(len(percentile)):
	offset += 0.02
	percent = percentile[i]
	plt.plot(xaxis, results[percent], colors[i%10], linestyle='-', marker=markers[i%11], markevery=0.1+offset,
                label=str(percentile[i])+'th%-tile FCT', markersize=10, linewidth='2')
	plt.yticks(rotation=45)
	plt.grid(True, which="both")
	plt.xlabel(r'$\alpha$')
	plt.xscale('log')
	#plt.yscale('log')
	plt.ylabel('Flow Completion Time (s)')
	plt.legend()

outfilename = outfilename_prefix + "_fct_all_alpha.png"
plt.tight_layout()
plt.savefig(outfilename, dpi=600)
plt.clf()

