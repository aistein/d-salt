#!/usr/bin/python

import sys
import csv
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.size'] = 16
matplotlib.rcParams['xtick.labelsize'] = 14
matplotlib.rcParams['ytick.labelsize'] = 14
fig_size = plt.rcParams["figure.figsize"]
print(fig_size)
#fig_size[0] = 4.4


try:
    filename = sys.argv[1]
#    cutoff_rank = long(sys.argv[2])
except:
    exit("usage: ./prio_time_series.py <path to raw prio file>")
markers = ['o', 'x']
colors = ['blue', 'red']

#flowid = ['1031023108','196516021'] # size-blind w5_a10.xml
flowid = ['3589491499','1181154501'] # size-aware w5_a6.xml
#print(flowid)
prio_values = {}
count = 0
with open(filename, 'r') as f:
    reader = csv.reader(f, delimiter=',')
    for row in reader:
	if len(row) < 7000 and len(row) > 4000:
		print row[0]
		#flowid = [row[0]]
	if count == 3:
		break
        if row[0] in flowid:
		print("here")
		prio_values[row[0]] = []
		count += 1
	else:
		continue
	rawprio_ts = []
	for i in range(4, len(row)-2, 3):
            if float(row[i]) != 0.0:
                rawprio_ts.append(math.log(float(row[i]),2))
	prio_values[row[0]] = rawprio_ts
#print(prio_values)
legends = []
i = 0 
for key in prio_values:
	#plt.scatter([x for x in range(len(prio_values[key][1900:]))], prio_values[key][1900:], label=key)
	plt.scatter([x for x in range(1,len(prio_values[key])+1)], prio_values[key], label=key, color=colors[i], marker=markers[i])
	i += 1
	legend = 'flow id = ' + key
	legends.append(legend)
plt.legend(legends)
plt.tight_layout()


#sorted_rawprios = [tup[0] for tup in sorted(rawprio_ts, key=lambda tup : tup[0])]
#print "number of samples = {}".format(len(sorted_rawprios))


#plt.plot([k for k in range(len(sorted_rawprios))], sorted_rawprios, linestyle='-')
plt.xlabel("Packet sequence number")
plt.ylabel("Log2 (Priority Value)")
#plt.yscale('symlog')
plt.savefig('flowtimeseries.png', dpi=600)

# Zoom in plot
plt.clf()
fig, axs = plt.subplots(2)
fig.text(0.02, 0.5, 'Log2 (Priority Value)', va='center', rotation='vertical')
# add a big axis, hide frame
#fig.add_subplot(111, frameon=False)
# hide tick and tick label of the big axis
#plt.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
#plt.ylabel("Log2 (Priority Value)")
#fig.suptitle('Vertically stacked subplots')
key = flowid[1]
start=500
end=515
axs[0].plot([x for x in range(start,start+len(prio_values[key][start:end]))], prio_values[key][start:end], label=key, markersize=10, marker='o', color='blue')
legend = "flow id = " + key
axs[0].legend([legend])

key = flowid[0]
start=800
end=820
axs[1].plot([x for x in range(start,start+len(prio_values[key][start:end]))], prio_values[key][start:end], label=key, markersize=10, marker='x', color='red')
legend = "flow id = " + key
axs[1].legend([legend])
plt.xlabel("Packet sequence number")
#plt.ylabel("Log2 (Priority Value)")
#plt.yscale('symlog')
#plt.tight_layout()
left = 0.125  # the left side of the subplots of the figure
right = 0.9   # the right side of the subplots of the figure
bottom = 0.1  # the bottom of the subplots of the figure
top = 0.9     # the top of the subplots of the figure
wspace = 0.2  # the amount of width reserved for space between subplots,
              # expressed as a fraction of the average axis width
hspace = 0.2  # the amount of height reserved for space between subplots,
              # expressed as a fraction of the average axis height
plt.subplots_adjust(wspace=0.2, hspace=0.3, left=0.2, bottom=0.12, right=0.96, top=0.96)
#plt.subplots_adjust(wspace=0.6, hspace=0.6, left=0.5, bottom=0.22, right=0.96, top=0.96)

plt.savefig('flowtimeseries_zoom.png', dpi=600)
