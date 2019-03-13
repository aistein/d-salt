#!/usr/bin/python3

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

cdf_files = []
cdf_files.append("./sizeDistributions/FacebookKeyValue_Sampled.txt")
cdf_files.append("./sizeDistributions/Google_SearchRPC.txt")
cdf_files.append("./sizeDistributions/Google_AllRPC.txt")
cdf_files.append("./sizeDistributions/Facebook_HadoopDist_All.txt")
cdf_files.append("./sizeDistributions/DCTCP_MsgSizeDist.txt")

colors = ['tab:blue', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown']
markers = ["x", "o", "v", "s", "d"]

fig, ax = plt.subplots()
offset = 0.0
for i, cdf_file in enumerate(cdf_files):
    workload = i+1
    with open(cdf_file, 'r') as f:
        next(f)
        flowsizes = []
        cumprobs = []
        for line in f:
            fields = line.split()
            flowsizes.append(float(fields[0]))
            cumprobs.append(float(fields[1]))
        offset += 0.02
        plt.plot(flowsizes, cumprobs, colors[i], linestyle='-', marker=markers[i], markevery=0.1+offset,
                label="W{}".format(workload))
        print("Finished Plotting W{}".format(workload))

plt.rcParams.update({'font.size': 12})
plt.xlabel("Flow Size (bytes)", fontsize=12)
plt.xticks(fontsize=12)
plt.xscale('log')
plt.ylabel("Cumulative Probability", fontsize=12)
plt.yticks(fontsize=12)
plt.legend()
plt.tight_layout()
plt.savefig("./workload_distributions.png")
plt.clf()
