#!/usr/bin/python3

import sys
from collections import defaultdict
from numpy.random import uniform

# read CLI arguments
try:
    cdf_file = sys.argv[1]
    ip_file = sys.argv[2]
    ipoutdir = sys.argv[3]
    num_samples = int(sys.argv[4].strip())
except IndexError:
    print("usage: ./sample_from_cdf.py <cdf_file> <ip_list> <ip_out_dir> <num_samples>")
    exit()

# read CDF into an array
cdf = []
with open(cdf_file, 'r') as cdf_fh:
    # get the MTU
    mtu = float(next(cdf_fh).strip())
    print("MTU: {}".format(mtu))
    for line in cdf_fh:
        datapoint = [float(f) for f in line.split()] # n-mtus cum-prob
        cdf.append(datapoint)

# get a set of K samples from the CDF
def GetSamples():
    samples = defaultdict(int)
    for _ in range(num_samples):
        u = uniform()
        prev_cum_prob = cdf[0][1]
        if u < prev_cum_prob:
            sample = cdf[0][0]
            continue
        for i, datapoint in enumerate(cdf[1:],0):
            curr_cum_prob = datapoint[1]
            if prev_cum_prob < u and u <= curr_cum_prob:
                sample = datapoint[0]
                break
            prev_cum_prob = curr_cum_prob
        samples[sample] += 1

    # terminal-based histogram - for debugging only
    # for val, cnt in sorted(samples.items(), key=lambda sample : sample[0]):
    #     pstr = "{: <15} : ".format(val)
    #     for _ in range(cnt):
    #         pstr += '|'
    #     print(pstr)
    return samples



def main():
    with open(ip_file, 'r') as ip_fh:
        for ip in ip_fh:
            fname = ipoutdir + '/' + ip.strip() + '.samples'
            with open(fname, 'w') as ip_ofh:
                print("Generating samples for {}...".format(ip.strip()))
                samples = GetSamples()
                for val, cnt in sorted(samples.items(), key=lambda sample : sample[0]):
                    for _ in range(cnt):
                        ip_ofh.write("{}\n".format(mtu * val))
                        print(mtu * val)

if __name__ == "__main__":
    main()
