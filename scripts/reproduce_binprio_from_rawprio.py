#!/usr/bin/python3

import sys
import csv

try:
    rawprio_file = str(sys.argv[1])
    profile = int(sys.argv[2])
    tag = str(sys.argv[3])
    scenario = str(sys.argv[4])
except:
    exit("usage: ./reproduce_binprio_from_rawprio.py <rawprio_file> <profile> <tag> <scenario>")

BINS = 8

if scenario == 'omniscient':
    binprio_boundaries_by_profile = {
                1: [7.7308E-40, 4.5136E-40, 2.6352E-40, 1.5386E-40, 8.9828E-41, 5.2446E-41, 3.0620E-41, 1.7878E-41],
                2: [3.7e-07, 4.8e-18, 6.3e-29, 8.24e-40, 1.07e-50, 1.41e-61, 1.84e-72, 3.13e-94],
                3: [4.08e-06, 3.95e-17, 3.82e-28, 3.69e-39, 3.58e-50, 3.45e-61, 3.34e-72, 3.24e-82],
                4: [1.62e-05, 1.32e-16, 1.07e-27, 8.76e-39, 7.13e-50, 5.8e-61, 4.72e-72, 3.84e-83],
                5: [4.71e-05, 3.94e-16, 3.3e-27, 2.76e-38, 2.31e-49, 1.94e-60, 1.62e-71, 1.36e-82]
        }
elif scenario == 'blind':
    binprio_boundaries_by_profile = {
                1: [2.5e-19, 1e-21, 4.4e-24, 1.9e-26, 7.8e-29, 3.3e-31, 1.4e-33, 5.8e-36],
                2: [6.1e-20, 1.5e-23, 3.6e-27, 8.7e-31, 2.1e-34, 5.1e-38, 1.2e-41, 2.9e-45],
                3: [5.8e-21, 7.3e-26, 9e-31, 1.1e-35, 1.3e-40, 1.6e-45, 2e-50, 2.5e-55],
                4: [2.6e-21, 1.2e-26, 5.3e-32, 2.4e-37, 1.1e-42, 4.9e-48, 2.2e-53, 1e-58],
                5: [1.2e-21, 2.7e-27, 6e-33, 1.3e-38, 3e-44, 6.5e-50, 1.4e-55, 3.2e-61]
        }
else:
    exit("invalid scenario: use (blind/omniscient)")

print("BinPrio Boundaries:")
print(binprio_boundaries_by_profile[profile])

timebounds_file = "w{}_{}_timebounds.txt".format(profile, tag)
with open(timebounds_file, 'r') as tbf:
    timebounds = [int(l.strip()) for l in tbf.readlines()]
print("Timebounds:")
print(timebounds)

binprio_file = "w{}_{}.prio".format(profile, tag)
bytes_by_binprio_global = [0 for _ in range(BINS)]
with open(rawprio_file, 'r') as rpf, open(binprio_file, 'w') as bpf:
    rpr = csv.reader(rpf, delimiter=',')
    bpw = csv.writer(bpf, delimiter=',')
    for line in rpr:
        flowid = line[0]
        bytes_by_binprio_local = [0 for _ in range(BINS)]
        for i in range(1, len(line)-3, 3):
            rawprio, size, age = float(line[i]), int(line[i+1]), int(line[i+2])
            #if age > timebounds[1]:
            #    continue
            #print("packet[{}]: rawprio = {}, size = {}".format(i//3, rawprio, size))
            if i//3 == 0: # TCP-Handshaking
                bytes_by_binprio_local[0] += size
                bytes_by_binprio_global[0] += size
                continue
            for binprio in range(BINS-1, -1, -1): # Data Packets
                if rawprio <= binprio_boundaries_by_profile[profile][binprio]:
                    bytes_by_binprio_local[binprio] += size
                    bytes_by_binprio_global[binprio] += size
                    break
        bpw.writerow([flowid,] + bytes_by_binprio_local)

print("BinPrio Bytes:")
print(bytes_by_binprio_global)
