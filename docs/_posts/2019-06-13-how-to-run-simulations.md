---
excerpt: Instructions on how to run various tests using D-SALT on an 144-node NS3-simulated datacenter architecture, for the CDF-based workload trace and incast scenarios.
---

All parties having been granted access to this project should have `sudo` priveleges on our gcloud instances; logging in with your own username and password will suffice.  The location of the D-SALT source code and run scripts is `/data/repositories/d-salt`.  

Both of the test-suites described here run on our 144-node topology: 4 "core" switches connected to 9 "edge" (or ToR) switches over 40Gbps links, where each ToR switch is in turn connected to 16 end-hosts over 10Gbps links.  As described, this topology defaults to 1:1 oversubscription, but can easily be switched to 2:1 by setting the flag `oversub=true` in the configuration file.

***Caution:*** These simulations can take many hours to run, even on very powerful machines; We strongly recommend deploying them either inside of a `tmux` session or prefixed with `nohup`.

## Simulating Workloads 1 - 5
We use CDFs derived from 5 real-world datacenter workload traces: W1 is from Facebook Mecached, W2 is Google Search, W3 is an Aggregation of Applications from Google, W4 is from a Facebook Hadoop cluster, and W5 is the Microsoft Web Search trace from Microsoft.  These are the very same CDFs used to evaluate the Homa datacenter transport protocol.  For each workload ("profile"), flow sizes are sampled from the corresponding CDF, and are dispatched according to a Poisson process for which lambda is set to some target workload (default 80%, configurable).

### Configurations
The `d-salt/run_pipeline` bash script takes as its argument a configuration file, templates for which can be found in `d-salt/config-templates`.  Broadly, this script can deploy simualtions for workloads 1-5, each having various values for alpha, and with several switches that can change switch configurations like buffer-size and DCTCP K-value.  This script waits for all simulations to finish, and then optionally runs a battery of plotting and analysis scripts, which can be pushed to our GCS bins if `upload=true` in the configuration file.  Here is a sample config-file `run_pipeline-template.conf':
  ```bash
  #!/bin/bash

  #---------- begin user configurations -------------------------
  # ns3 build area
  ns3='./ns3.29-workspace-dev'

  # number of processors on this machine
  processors=10

  # number of flows to send
  flows=300000

  # queue buffer size
  buff=42400

  # DCTCP threshold
  thresh=10

  # PBS Alpha Values
  alphas=(10 1000) # blind alphas

  # Workload Profiles
  profiles=(1 2 3 4 5)

  # Desired Network Load
  load=0.8

  # Load Multipliers
  load_multipliers=(3.5 4 5 6 7) # 1:1 samethresh @80% load mutlipliers

  # Oversubscribed?
  oversub=false

  # Nonblind?
  nonblind=false

  # Same DCTCP Thresholds?
  samethresh=false

  # Description of this Experiment
  description="80% Load, W1-5, 1:1 Subscription, Blind"

  # Pipeline Script Control Switches
  run_simulations=true # if false, expects pre-populated tmp dir
  upload=true # if true, upload results to GCS
  clean=true # if true, remove all temporary files
  categorize_flows=true # generate flow category plots
  without_dctcp=false # add "without_dctcp" to sims
  scatterplots=false # graph slowdown & fct scatters
  #----------- end user configurations --------------------------
  ```

### Run Command
Kick off the script in a recoverable environment in case your connection to the server is interrupted.  Make sure all desired configurations are updated in the config-file before moving forward

```bash
$ cd /data/repositories/d-salt
$ cp config-templates/run_pipeline-template.conf ./my_config.conf
$ vim my_config.conf
$ tmux new -s run
$ ./run_pipeline my_config.conf
```

### Outputs
-TODO-

## Simulating Incast
It is well known in the datacenter community that the proliferation of partiton-aggregate data transfer patterns inherent to applications like MapReduce can cause temporary buffer pressure and abnormal packet-loss.  As such, no datacenter transport protocol can be deemed effective without being shown to overcome this "incast" issue.  We evaluate D-SALT's incast tolerance using the same tests as NDP: sweep the number of simultaneous senders (all having the exact same target receiver) from 1 up to 128 and observe the resultant growth and variance in min/max flow completion time (FCT).

### Configurations
Configurations for incast simulations are largely the same as those for W1-5 simulations, save for some important exceptions.  The number of simultaneous senders (the "incast degree") is set by the parameter `senders`; the number of flows sent per sender is controlled by `flows`; the choice to test every incast-degree from 1 up to `senders` is controlled by the `sweepdegrees` flag; the size of each flow (in bytes) is set by `flowsize`.  A template for the incast configuration can be also be found in `d-salt/config-templates`:
  ```bash
  #!/bin/bash

  #---------- begin user configurations -------------------------
  # ns3 build area
  ns3='./ns3.29-workspace-dev'

  # number of processors on this machine
  processors=16

  # number of flows per incast degree
  flows=1000

  # number of incast senders
  senders=128

  # sweep from 1 to N incast senders?
  sweepdegrees=true

  # debug - enable Pcap for all nodes
  debug=false

  # size of each incast flow
  flowsize=450000

  # queue buffer size
  buff=42400

  # same buff for PBS & DCTCP?
  same_buff=false

  # DCTCP threshold
  thresh=10

  # Nonblind?
  nonblind=true

  # PBS Alpha Values
  alphas=(10)

  # same threshold
  samethresh=false

  # description of this experiment
  description="Incast Scenario for 128-nodes, Omniscient, 450kB flows, Alpha=10, 1000-per-degree"

  # Plot Generation Switches
  run_simulations=true # if false, expects pre-populated tmp dir
  upload=false # if true, upload results to GCS
  clean=false # if true, remove all temporary files
  #----------- end user configurations --------------------------
  ```

### Run Command
As previously stated, we suggest that you kick off the script in a recoverable environment in case your connection to the server is interrupted.  Make sure all desired configurations are updated in the config-file before moving forward

```bash
$ cd /data/repositories/d-salt
$ cp config-templates/incast_run_pipeline-template.conf ./my_incast_config.conf
$ vim my_config.conf
$ tmux new -s incast_run
$ ./incast_run_pipeline my_incast_config.conf
```

### Outputs
-TODO-