---
excerpt: Instructions on how to run various tests using D-SALT on an 144-node NS3-simulated datacenter architecture
---

## Workloads 1 - 5

All parties having been granted access to this project should have `sudo` priveleges on our gcloud instances; logging in with your own username and password will suffice.  The location of the D-SALT source code and run scripts is `/data/repositories/d-salt`.

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

*Caution:* These simulations can take many hours to run, even on very powerful machines; We strongly recommend deploying them either inside of a `tmux` session or prefixed with `nohup`.

Kick off the script in a recoverable environment in case your connection to the server is interrupted.  Make sure all desired configurations are updated in the config-file before moving forward

```bash
$ cd /data/repositories/d-salt
$ cp config-templates/run_pipeline-template.conf ./my_config.conf
$ vim my_config.conf
$ tmux new -s run
$ ./run_pipeline my_config.conf
```