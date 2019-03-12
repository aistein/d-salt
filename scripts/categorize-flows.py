#!/usr/bin/python

import numpy as np
import csv
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    filename = sys.argv[1]
    testname = filename.strip().split('/')[2].split('.')[0]
except IndexError:
    print("usage: ./categorize-flows.py <category file>.categories")
    exit(1)

N_CATEGORIES = 3
N_PRIORITIES = 8

flowdict = {}
with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    next(reader)
    for row in reader:
        flowdict[row[0]] = map(int,row[1:N_PRIORITIES+2]) # key=flow_id, values=bytes_array

flowsizes = sorted([bytes_array[0] for bytes_array in flowdict.itervalues()]) # bytes_array[0]=total_bytes
categorylimits = np.logspace(np.log10(min(flowsizes)), np.log10(max(flowsizes)), num=N_CATEGORIES+2, dtype=int)[1:(1+N_CATEGORIES)]

bintotals = np.ones(shape=(N_PRIORITIES), dtype=int)
categorysums = np.zeros(shape=(N_CATEGORIES, N_PRIORITIES), dtype=int)
for flow_id, bytes_array in flowdict.items():
    for i in range(N_CATEGORIES):
        if bytes_array[0] <=  categorylimits[i]:
            for j in range(N_PRIORITIES):
                categorysums[i][j] += bytes_array[j+1]
                bintotals[j] += bytes_array[j+1]
            break

print categorysums

colors = ['#E69F00', '#56B4E9', '#F0E442']
names = ['Small-'+str(categorylimits[0]),'Medium-'+str(categorylimits[1]),'Large-'+str(categorylimits[2])]
small = categorysums[0].tolist()
medium = categorysums[1].tolist()
large = categorysums[2].tolist()
width = 0.25
ind = np.arange(N_PRIORITIES)

plt.figure()
p1 = plt.bar(ind, small, width, alpha=0.5, color=colors[0])
p2 = plt.bar(ind+width, medium, width, alpha=0.5, color=colors[1])
p3 = plt.bar(ind+2*width, large, width, alpha=0.5, color=colors[2])
plt.xticks(ind+1.5*width, ['P0','P1','P2','P3','P4','P5','P6','P7'])
plt.legend([p1[0],p2[0],p3[0]], names)
plt.title(testname + ' Flow Categories by Priority')
plt.xlabel("Priority Class")
plt.ylabel("Bytes (Norm) from S/M/L Category")
plt.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
outfilename = testname + "_categories.png"
plt.savefig(outfilename)
plt.clf()
