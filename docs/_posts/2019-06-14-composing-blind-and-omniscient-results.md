---
excerpt: D-SALT has two flavors, blind & omniscient.  Unfortunately, our implementation supports the simulation of only one such mode at a time.  This post describes how one can superimpose the results from separate runs so as to meaningfully compare the performance of each mode (or any other varying parameters).
---

***Caution:*** These simulations can take many hours to run, even on very powerful machines; We strongly recommend deploying them either inside of a `tmux` session or prefixed with `nohup`.

## Manually Generate 99th Percentile & CDF plots of Flow Completion Time

We have not yet added support for the automated simulating and merging of blind & omniscient mode D-SALT results.  In order to obtain relevant graphs and compare the modes, one must manually run the corresponding plot generation scripts.  The two most important plots are 99th percentile FCT and FCT CDF.  In this post, we describe how to plot these with results from vanilla DCTCP, blind D-SALT, and omniscient D-SALT on the same axes.

### Run Blind & Omniscient Simulations
In order for results from both simulations to fit within the same domain and range, all configuration parameters should be left the same between the two runs except for two or three.  Firt `nonblind` flag must be set `true` to enable omniscient mode, and `false` to default to blind mode.  Critically, you must set `clean=flase` otherwise the results from the first simulation will be prematurely deleted.  Optionally, set `upload=false` since it makes little sense to push incomplete results to GCS.
```bash
$ cd data/repositories/d-salt
$ tmux new -s blind_omniscient_run
$ ./run_pipeline blind.config & wait $!
$ ./run_pipeline omniscient.config & wait $!
```

### Merge Blind & Omniscient Results
Each simulation will have placed the required temporary outputs in `d-salt/tmp/<profile>/data` and/or `d-salt/results/<profile>/data`.  There are 6 files needed, 2 for each line in the desired plots: the simulation's flow-information in XML format, and the "time-boundaries" file which indicates the first/last moments during simulation when the network load is at or above the target value (80% default).  The latter of these files should already be in the central repo directory when the simulations complete if you have correctly set `clean=false`.
1. Copy XML files into the main repo folder:
    ```bash
    $ cd data/repositories/d-salt
    $ cp tmp/<profile>/data/w<profile>_a<alpha>_blind.xml .
    $ cp tmp/<profile>/data/w<profile>_a<alpha>_omniscient.xml .
    $ cp tmp/<profile>/data/w<profile>_dctcp.xml .
    ```
2. Generate the plots in a recoverable environment as they make take a long time depending upon the profile:
    ```bash
    $ cd data/repositories/d-salt
    $ tmux new -s blind_omniscient_plot
    $ ./scripts/fct-cdf.py w<profile>_dctcp.xml w<profile>_a<alpha>_blind.xml w<profile>_a<alpha>_omniscient.xml
    $ ./scripts/fct-all-alpha.py w<profile>_dctcp.xml w<profile>_a<alpha>_blind.xml w<profile>_a<alpha>_omniscient.xml
    ```
3. Copy the generated plots from the server to your local machine to view:
    ```bash
    $ gcloud compute scp <cuid>_columbia_edu@homa-pbs-dctcp:/home/<cuid>_columbia_edu/d-salt/*.png <local-folder>
    ```