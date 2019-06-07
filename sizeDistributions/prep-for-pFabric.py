import os
import sys

f = open(sys.argv[1], "r")
f_out = open(sys.argv[2]+"_CDF.tcl", 'w')
total_bytes = 0
last_percent = 0
for cnt, line in enumerate(f) :
    #print("Line {}: {}".format(cnt, line[:-1]))
    line = line[:-1] # remove new line
    if cnt == 0 :
        print("Average: {}".format(line))
    else:
        line = line.split(" ")
        line = list(filter(None, line))
        #print(line)
        #print("line 0: {}".format(line[0]))
        #print("line 1: {}".format(line[1]))
        num_bytes = float(line[0])
        percent = float(line[1])

        total_bytes += num_bytes * (percent - last_percent)
        last_percent = percent

        num_bytes /= 1000
        if cnt == 1 :
            f_out.write("{} 1 0\n".format(num_bytes))
        f_out.write("{} 1 {}\n".format(num_bytes,percent))

print("True Average: {}".format(total_bytes))

f.close()
f_out.close()




