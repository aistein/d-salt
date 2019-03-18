# D-SALT
### Datacenter Sender Adaptive Low-Latency Transport
#### Dr. Vishal Misra (misra@cs.columbia.edu), Dr. Dan Rubenstein (danr@cs.columbia.edu), Kunal Mahajan (kvm2116@columbia.edu), Pearce Kieser (pck2119@columbia.edu), Yudong Yang (yy2485@columbia.edu), Alexander Stein (as5281@columbia.edu)
##### Columbia University


## IMPORTANT FILES
	/data/repositories/homa/ns3simulation/pbs/model/
		- contains entire PBS host filter implementation
		- decided packet priority class mapping limits
		- records important statistics about PBS host filter
	/data/repositories/homa/ns3simulation/pbs-switch/model/
		- contains entire PBS switch filter implementation
		- ensures PBS determined priorities are passed through switches
		- records important statistics about PBS switch filter
	/data/repositories/homa/ns3simulation/homatopology.cc
		- contains workload gen
		- contains PBS packet filter + Priority Queue instantiation
		- contains all settings for switches
		- contains simulation run

## RUN ALL SIMULATIONS
	cd /data/repositories/homa/ns3simulation
	./run_pipeline
		- edit top section of "run_pipeline" file to change simulation configs
