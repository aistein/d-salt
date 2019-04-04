/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2019 
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 * Authors: Kunal Mahajan <mkunal@cs.columbia.edu>, Alex Stein <as5281@columbia.edu>,
 * 	    Pearce Kieser <pck2119@columbia.edu>
 */

#include <iostream>
#include <fstream>
#include <string>
#include <cassert>
#include <cstdio>
#include <ctime>

#include <algorithm>
#include <vector>
#include <cctype>
#include <locale>

#include "ns3/log.h"
#include "ns3/applications-module.h"
#include "ns3/bridge-helper.h"
#include "ns3/bridge-net-device.h"
#include "ns3/core-module.h"
#include "ns3/csma-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/ipv4-nix-vector-helper.h"
#include "ns3/network-module.h"
#include "ns3/nstime.h"
#include "ns3/point-to-point-module.h"
#include "ns3/prio-queue-disc.h"
#include "ns3/packet.h"
#include "ns3/packet-filter.h"
#include "ns3/pbs.h"
#include "ns3/traffic-control-helper.h"
#include "ns3/prioTag.h"
#include "ns3/pbs-switch.h"
/*
	- This work goes along with the paper "Towards Reproducible Performance Studies of Datacenter Network Architectures Using An Open-Source Simulation Approach"

	- The code is constructed in the following order:
		1. Creation of Node Containers 
		2. Initialize settings for On/Off Application
		3. Connect hosts to edge switches
		4. Connect edge switches to aggregate switches
		6. Start Simulation

	- Addressing scheme:
		1. Address of host: 10.0.edge.0 /24
		2. Address of edge and aggregation switch: 10.0.edge.0 /16
		
	- TODO: Descibre BulkSend Application and remove On/Off description
	- On/Off Traffic of the simulation: addresses of client and server are randomly selected everytime
		1. On - Timing Sampled from EmpiricalRandomVariable (created via CDF supplied from command line)
		2. Off - Timing Sampled from UniformRandomVariable // TODO: what should the "off" time actually be?
	
	- Simulation Settings:
                - Number of nodes: 16*4 = 144
		- Simulation running time: 6 seconds
		- Packet size: 1024 bytes
		- Data rate for packet sending: 1 Mbps
		- Data rate for device channel: 1000 Mbps
		- Delay time for device: 0.001 ms
		- Communication pairs selection: Random Selection with uniform probability
		- Traffic flow pattern: Exponential random traffic
		- Routing protocol: Nix-Vector

        - Statistics Output:
                - Flowmonitor XML output file: homastats.xml is located in the ns-3.29/ folder
		- TODO: describe all other outputs            


*/


/*
generate plots with (from ~/library/Projects/DS-NetowrksSchedulingResearch$):
```
sudo gsutil -m cp -r gs://homa-pbs/SmallFlow_Debug/ *.xml .
python git_workspace/homa/ns3simulation/scripts/fct-cdf-smallFlows.py small_debug.xml
```
*/

using namespace ns3;
using namespace std;
NS_LOG_COMPONENT_DEFINE ("Homa-Architecture");

// Function to create address string from numbers
//
char * toString(int a,int b, int c, int d){

	int first = a;
	int second = b;
	int third = c;
	int fourth = d;

	char *address =  new char[30];
	char firstOctet[30], secondOctet[30], thirdOctet[30], fourthOctet[30];	
	//address = firstOctet.secondOctet.thirdOctet.fourthOctet;

	bzero(address,30);

	snprintf(firstOctet,10,"%d",first);
	strcat(firstOctet,".");
	snprintf(secondOctet,10,"%d",second);
	strcat(secondOctet,".");
	snprintf(thirdOctet,10,"%d",third);
	strcat(thirdOctet,".");
	snprintf(fourthOctet,10,"%d",fourth);

	strcat(thirdOctet,fourthOctet);
	strcat(secondOctet,thirdOctet);
	strcat(firstOctet,secondOctet);
	strcat(address,firstOctet);

	return address;
}

int subnet_counter = 0; // keep incrementing count of which subnets have been assigned 


// Function to get a new subent
char * nextNet(){

	int first = 11;
	int second = (subnet_counter / 256) % 256;
	int third = subnet_counter % 256;
	int fourth = 0;
    subnet_counter++;
	return toString(first,second,third,fourth);
}

// For progress reporting
void
 ReportStart(uint64_t appNumber, uint64_t totalNumber) 
 {
   time_t now = time(0);
   tm *ltm = localtime(&now);

   std::cout << "[Progress " << 1 + ltm->tm_hour << ":" << 1 + ltm->tm_min << ":" << 1 + ltm->tm_sec << "] Sending app " << appNumber << " of " << totalNumber << "\n";
 }

 void
 ProgressTracking (int period, uint32_t sim_duration, double micro_sec_count, double alpha_entry, bool use_pbs_value)
 {
   Simulator::Schedule (MicroSeconds (period), &ProgressTracking, period, sim_duration, (micro_sec_count+period), alpha_entry, use_pbs_value);
   double percent = micro_sec_count;
   percent = percent / sim_duration * 100;
   time_t now = time(0);
   tm *ltm = localtime(&now);
   
   //std::cout << "Total duration = " << sim_duration << " us\n";
   //std::cout << "program time = " << micro_sec_count << " us\n";
   //std::cout << "simulation time = " << Simulator::Now().GetMicroSeconds() << " us\n";
   if (!use_pbs_value) {
	   alpha_entry = -1;
   }

   std::cout << "[a = " << alpha_entry << ", progress " << 1 + ltm->tm_hour << ":" << 1 + ltm->tm_min << ":" << 1 + ltm->tm_sec << "] " << percent << " percent complete" << std::endl;
 }


// Main function
//
int main(int argc, char *argv[])
{
//============= Enable Command Line Parser & Custom Options ================//
//
	uint32_t profile = 1;
	string tag = "";
	double alpha = 0.001;
	uint32_t num_flows = 1;
	bool fast = false;
	bool use_pbs = true;
	bool use_dctcp = true;
	uint32_t buffer_size = 42400;
	uint32_t threshold = 10;
	double load_multiplier = 6.0; // increase the load by a constant factor to account for TCP slow-start inefficiency!
        double load = 0.6; // load percentage
	int incast_servers = 1;
	double time_per_smallFlow = 3;
	int progress_period = 1;

	CommandLine cmd;
	cmd.AddValue("profile", "identifier of the workload distribution to be tested (int)", profile);
	cmd.AddValue("tag", "desired postfix for output files (string)", tag);
	cmd.AddValue("alpha", "tunable parameter dictating scheduling policy (double)", alpha);
	cmd.AddValue("fast", "speed up simulation by using Mbps links instead of Gbps links (bool)", fast);
	cmd.AddValue("apps", "how many apps to run (int)", num_flows);
	cmd.AddValue("buff", "buffer size of each switch (int)", buffer_size);
	cmd.AddValue("thresh", "dctcp threshold value (int)", threshold);
	cmd.AddValue("usePbs", "switch to toggle PBS mode (bool)", use_pbs);
	cmd.AddValue("useDctcp", "switch to toggle DCTCP mode (bool)", use_dctcp);
	cmd.AddValue("load", "load factor (double)", load);
	cmd.AddValue("loadMultiplier", "load factor multiplier to increase number of flows (double)", load_multiplier);
	cmd.AddValue("incast_servers", "number of incast servers (int)", incast_servers);
	cmd.AddValue("time_per", "time spacing constant for scheduling small flows (ms)", time_per_smallFlow);
	cmd.AddValue("progress_period", "INT time spacing constant progress reports (us).  Setting 0 will disable output.", progress_period);
	cmd.Parse (argc, argv);

	string cdf_filename = "";
	string output_directory = "";
	uint32_t sim_duration = 6000;

    if (profile != 7) {
        cout << "ERROR not supported workload profile only for smallflow (7)\n";
        return -1;
    }

	switch (profile)
	{
		case 1: // W1
			cdf_filename = "./sizeDistributions/FacebookKeyValue_Sampled.txt";
			output_directory = "./results/W1/";
			tag = "w1_" + tag;
			break;
		case 2: // W2
			cdf_filename = "./sizeDistributions/Google_SearchRPC.txt";
			output_directory = "./results/W2/";
			tag = "w2_" + tag;
			break;
		case 3: // W3
			cdf_filename = "./sizeDistributions/Google_AllRPC.txt";
			output_directory = "./results/W3/";
			tag = "w3_" + tag;
			sim_duration = 9000;
			break;
		case 4: // W4
			cdf_filename = "./sizeDistributions/Facebook_HadoopDist_All.txt";
			output_directory = "./results/W4/";
			tag = "w4_" + tag;
			sim_duration = 24000;
			break;
		case 5: // W5
			cdf_filename = "./sizeDistributions/DCTCP_MsgSizeDist.txt";
			output_directory = "./results/W5/";
			tag = "w5_" + tag;
			sim_duration = 24000;
			break;
		case 6: // incast
			output_directory = "./results/incast/";
			tag = "incast_" + tag;
			sim_duration = 24000;
			break;
        case 7: // small flow impact among large flows
            output_directory = "./results/small/";
            tag = "small_" + tag;
            sim_duration = time_per_smallFlow * 1000 * (num_flows); //sim_duration is in us
            break;
	}

//=========== Define FatTree Topology ===========//
// total number of hosts = 432 = 12**3 / 4
    int k = 12;			// number of ports per switch
	// NOTE verify before assuming this works for odd k
	int num_pod = k;		// number of pod
	int num_host = (k/2);		// number of hosts under a switch
	int num_edge = (k/2);		// number of edge switch in a pod
	int num_agg = (k/2);		// number of aggregation switch in a pod
	int num_group = k/2;		// number of group of core switches
    int num_core = (k/2);		// number of core switch in a group
	int total_host = k*k*k/4;	// number of hosts in the entire network	
	string filename = output_directory + tag + ".xml";	// filename for Flow Monitor xml output file

// Define variables for BulkSend Application
// These values will be used to serve the purpose that addresses of server and client are selected randomly
// Note: the format of host's address is 10.pod.switch.(host+2)
//
	srand( time(NULL) );

//	int target_swRand = 0;		// Random values for servers' address
//	int target_hostRand = 0;	//

// Initialize other variables
//
	int i = 0;	
	int j = 0;	
	int h = 0;

// Initialize parameters for BulkSend application(s)
//
	int port = 9;
	cout << "Number of Small Flows = " << num_flows << "\n";
	cout << "Total simulation time = " << sim_duration << " us\n";

// Initialize parameters for Csma and PointToPoint protocol
//
	std::string rateUnits = "Gbps";
	if (fast) {
		rateUnits = "Mbps";
	}
	std::cout << "Link Rate Units = " << rateUnits << "\n";
	
// Output some useful information
//	
	std::cout << "Total number of hosts =  "<< total_host<<"\n";
	std::cout << "Number of hosts under each switch =  "<< num_host<<"\n";
	std::cout << "Number of edge switch under each pod =  "<< num_edge<<"\n";
	std::cout << "Number of ports per switch =  " << k << "\n";
	std::cout << "------------- "<<"\n";

	ns3::PacketMetadata::Enable ();

// Initialize Internet Stack and Routing Protocols
//	
	// Basic Settings
	if (use_pbs) {
		buffer_size /= 8;
	}
	Config::SetDefault ("ns3::Ipv4GlobalRouting::RandomEcmpRouting", BooleanValue (true));
	Config::SetDefault ("ns3::TcpSocketBase::EcnMode", StringValue ("ClassicEcn"));
	Config::SetDefault ("ns3::RedQueueDisc::QW", DoubleValue (1));
	Config::SetDefault ("ns3::RedQueueDisc::UseHardDrop", BooleanValue (false));
	Config::SetDefault ("ns3::RedQueueDisc::LinkDelay", TimeValue (NanoSeconds(0)) );
	Config::SetDefault ("ns3::RedQueueDisc::MaxSize", QueueSizeValue (QueueSize (to_string(buffer_size) + "p")));
	// DCTCP Settings
	if (use_dctcp) {
		Config::SetDefault ("ns3::TcpL4Protocol::SocketType", TypeIdValue (TcpDctcp::GetTypeId ()));
		Config::SetDefault ("ns3::RedQueueDisc::MinTh", DoubleValue (threshold));
		Config::SetDefault ("ns3::RedQueueDisc::MaxTh", DoubleValue (threshold));
		Config::SetDefault ("ns3::RedQueueDisc::UseEcn", BooleanValue (true));
	}

	InternetStackHelper internet;

//=========== Creation of Node Containers ===========//
//
	NodeContainer core[num_group];				// NodeContainer for core switches
	for (i=0; i<num_group;i++){  	
		core[i].Create (num_core);
		internet.Install (core[i]);		
	}
	NodeContainer agg[num_pod];				// NodeContainer for aggregation switches
	for (i=0; i<num_pod;i++){  	
		agg[i].Create (num_agg);
		internet.Install (agg[i]);
	}
	NodeContainer edge[num_pod];				// NodeContainer for edge switches
  	for (i=0; i<num_pod;i++){  	
		edge[i].Create (num_edge);
		internet.Install (edge[i]);
	}
	NodeContainer host[num_pod][num_edge];		// NodeContainer for hosts
  	for (i=0; i<num_pod;i++){
		for (j=0;j<num_edge;j++){  	
			host[i][j].Create (num_host);		
			internet.Install (host[i][j]);
		}
	}

//=========== Connect edge switches to hosts ===========//

// NetDeviceContainer for Network Load calculation via tracing
//
        NetDeviceContainer networkLoadTracer;

// Initialize Traffic Control Helper
//
	TrafficControlHelper tchHost;
	uint16_t handle = tchHost.SetRootQueueDisc ("ns3::PrioQueueDisc"); 
	tchHost.AddPacketFilter(handle, "ns3::PbsPacketFilter",
				"Alpha", DoubleValue (alpha),
				"Profile", UintegerValue (profile),
		       		"UsePbs", BooleanValue (use_pbs)
	);
	TrafficControlHelper::ClassIdList cls = tchHost.AddQueueDiscClasses (handle, 8, "ns3::QueueDiscClass"); 
	tchHost.AddChildQueueDiscs (handle, cls, "ns3::RedQueueDisc"); // Must use RED to support ECN
	QueueDiscContainer qdiscHost[num_pod][num_edge];

	TrafficControlHelper tchSwitch;
        uint16_t handleSwitch = tchSwitch.SetRootQueueDisc ("ns3::PrioQueueDisc"); 
	tchSwitch.AddPacketFilter(handle, "ns3::PbsSwitchPacketFilter");
        TrafficControlHelper::ClassIdList clsSwitch = tchSwitch.AddQueueDiscClasses (handleSwitch, 8, "ns3::QueueDiscClass"); 
        tchSwitch.AddChildQueueDiscs (handleSwitch, clsSwitch, "ns3::RedQueueDisc"); // Must use RED to support ECN
	QueueDiscContainer qdiscEdgeDown[num_pod][num_edge];
	QueueDiscContainer qdiscEdgeUp[num_pod][num_agg][num_edge];      
    QueueDiscContainer qdiscAgg[num_pod][num_agg][num_edge];


// Build topo
    Ipv4AddressHelper address;

	NetDeviceContainer hostSw[num_edge];		
	NetDeviceContainer pbsDevices[num_edge];
	NetDeviceContainer edgeDevicesDown[num_edge];
	Ipv4InterfaceContainer ipContainer[num_pod][num_edge];

	PointToPointHelper p2p_hostToEdge;
	p2p_hostToEdge.SetDeviceAttribute ("DataRate", StringValue ("10"+rateUnits));
  	p2p_hostToEdge.SetChannelAttribute ("Delay", StringValue ("10ns"));

	// connect hosts to edge
    for(h=0; h<num_pod;h++) {
		for(i=0; i<num_edge; i++) { // for each edge connect to num_host number of hosts
			for(j=0; j<num_host; j++) {
				NetDeviceContainer link = p2p_hostToEdge.Install( edge[h].Get(i), host[h][i].Get(j) );
				qdiscHost[h][i].Add ( tchHost.Install( link.Get (1) ) );
				qdiscEdgeDown[h][i].Add ( tchSwitch.Install( link.Get (0) ) );
				//Assign subnet
				address.SetBase ( nextNet(), "255.255.255.0");
				Ipv4InterfaceContainer tempContainer = address.Assign( link );
				ipContainer[h][i].Add (tempContainer.Get(1) );

				networkLoadTracer.Add( link.Get(0) );
			} 
		}
	}
	std::cout << "Finished connecting edge switches and hosts  "<< "\n";

//=========== Connect aggregate switches to edge switches ===========//
//

// Initialize PointtoPoint helper
//	
	PointToPointHelper p2p_edgeToAgg;
  	p2p_edgeToAgg.SetDeviceAttribute ("DataRate", StringValue ("10"+rateUnits));
  	p2p_edgeToAgg.SetChannelAttribute ("Delay", StringValue ("10ns"));
			     
// Installations...
    NetDeviceContainer ae[num_pod][num_agg][num_edge];
	Ipv4InterfaceContainer ipAeContainer[num_pod][num_agg][num_edge];
	for (i=0;i<num_pod;i++) {
		for (j=0;j<num_agg;j++){
			for (h=0;h<num_edge;h++){
				ae[i][j][h] = p2p_edgeToAgg.Install(agg[i].Get(j), edge[i].Get(h));
				qdiscEdgeUp[i][j][h] = tchSwitch.Install(ae[i][j][h].Get(1));
				qdiscAgg[i][j][h] = tchSwitch.Install(ae[i][j][h].Get(0));


				int second_octet = i;
				int third_octet = j+num_host;
				int fourth_octet;
				if (h==0) fourth_octet = 1;
				else fourth_octet = h*2+1;
				//Assign subnet
				char *subnet;
				subnet = toString(10, second_octet, third_octet, 0);
				//Assign base
				char *base;
				base = toString(0, 0, 0, fourth_octet);
				address.SetBase (subnet, "255.255.255.0", base);
				ipAeContainer[i][j][h] = address.Assign(ae[i][j][h]);
			}			
		}
	}	
	std::cout << "Finished connecting aggregation switches and edge switches  "<< "\n";

	//=========== Connect core switches to aggregate switches ===========//
    //
	NetDeviceContainer ca[num_group][num_core][num_pod]; 		
	Ipv4InterfaceContainer ipCaContainer[num_group][num_core][num_pod];
	int fourth_octet =1;

	PointToPointHelper p2p_aggToCore;
  	p2p_aggToCore.SetDeviceAttribute ("DataRate", StringValue ("10"+rateUnits));
  	p2p_aggToCore.SetChannelAttribute ("Delay", StringValue ("100ns")); 

	for (i=0; i<num_group; i++){		
		for (j=0; j < num_core; j++){
			fourth_octet = 1;
			for (h=0; h < num_pod; h++){			
				ca[i][j][h] = p2p_aggToCore.Install(core[i].Get(j), agg[h].Get(i)); 
				tchSwitch.Install(ca[i][j][h].Get(1));
				tchSwitch.Install(ca[i][j][h].Get(0));	

				int second_octet = k+i;		
				int third_octet = j;
				//Assign subnet
				char *subnet;
				subnet = toString(10, second_octet, third_octet, 0);
				//Assign base
				char *base;
				base = toString(0, 0, 0, fourth_octet);
				address.SetBase (subnet, "255.255.255.0",base);
				ipCaContainer[i][j][h] = address.Assign(ca[i][j][h]);
				fourth_octet +=2;
			}
		}
	}
	std::cout << "Finished connecting core switches and aggregation switches  "<< "\n";
	std::cout << "------------- "<<"\n";

//=========== Workload Generation (Unicast) ===========//
//
	// Small flow from one destination to one host
	ApplicationContainer app_small[num_flows];
	
	int target_pod = 0;
	int target_edge = 0;
    int target_host = 0;
	// Initialize Starting Time for the app on every host
	uint64_t app_start_time = 50;
	int src_pod = 1;
	int src_edge = 0; 
	int src_host = 0;
	uint64_t ui = 0;	


	for(ui = 0; ui < num_flows; ui++)
	{
		Ipv4Address targetIp = ipContainer[target_pod][target_edge].GetAddress(target_host);
                Address targetAddress = Address( InetSocketAddress( targetIp, port ));
                // Initialize BulkSend Application with address of target, and Flowsize
		uint32_t bytesToSend = 90000;
                BulkSendHelper bs = BulkSendHelper("ns3::TcpSocketFactory", targetAddress);
                bs.SetAttribute ("MaxBytes", UintegerValue (bytesToSend));
                bs.SetAttribute ("SendSize", UintegerValue (1460));
                // Install BulkSend Application to the sending node (client)
                NodeContainer bulksend;
                bulksend.Add(host[src_pod][src_edge].Get(src_host));
                app_small[ui] = bs.Install (bulksend);
                app_small[ui].Start (NanoSeconds (app_start_time));
				Simulator::Schedule (NanoSeconds (app_start_time), &ReportStart, ui+1, num_flows);
		app_start_time += (1000000 * time_per_smallFlow);   // add 'time_per_smallFlow' ms between two 90KB flows
	}

    // Packet Sink on all hosts
	for(h=0;h<num_pod;h++) {
		for(i=0;i<num_edge;i++){
                for(j=0;j<num_host;j++){
                    PacketSinkHelper sh = PacketSinkHelper("ns3::TcpSocketFactory",
                                                Address(InetSocketAddress(Ipv4Address::GetAny(), port)));       
                    sh.Install(host[h][i].Get(j));
                }
        }
	}

	// Generate Background traffic - 4 flows from each host to a random destination
	app_start_time = 50; // Initialize Starting Time for the app on every host
	ApplicationContainer app_long[(total_host-2)*4];
    port = 69;
	int app_counter = 0;
    for (h = 0; h < num_pod; h++) {
        for(i = 0; i < num_edge; i++)
        {
            for(j = 0; j < num_host; j++)
            {
                for(k = 0; k < 4; k++)
                {
                  if((i == 0 && j == 0) || (i == 1 && j == 0)){
                        break;
                    }
                    // Randomly pick a destination address
                    int target_podRand = rand() % num_pod;
                    int target_edgeRand = rand() % num_edge;
                    int target_hostRand = rand() % num_host;
                    while((target_podRand == 0 || target_podRand == 1) && target_edgeRand == 0 && target_hostRand == 0){
                        target_podRand = rand() % num_pod;
                        target_edgeRand = rand() % num_edge;
                        target_hostRand = rand() % num_host;
                    } // to make sure that destination does not belong to both the small flows hosts
                    Ipv4Address targetIp = ipContainer[target_podRand][target_edgeRand].GetAddress(target_hostRand);
                    Address targetAddress = Address( InetSocketAddress( targetIp, port ));
                    // Initialize BulkSend Application with address of target, and Flowsize
                    uint32_t bytesToSend = 0;
                    BulkSendHelper bs = BulkSendHelper("ns3::TcpSocketFactory", targetAddress);
                    bs.SetAttribute ("MaxBytes", UintegerValue (bytesToSend));
                    bs.SetAttribute ("SendSize", UintegerValue (1460));

                    // Install BulkSend Application to the sending node (client)
                    NodeContainer bulksend;
                    bulksend.Add(host[h][i].Get(j));
                    app_long[app_counter] = bs.Install (bulksend);
                    app_long[app_counter].Start (NanoSeconds(app_start_time));
                    app_counter += 1;
                }
            }
        }
    }
	// Packet Sink on all hosts
	for(h=0;h<num_pod;h++) {
		for(i=0;i<num_edge;i++){
                for(j=0;j<num_host;j++){
                    PacketSinkHelper sh = PacketSinkHelper("ns3::TcpSocketFactory",
                                                Address(InetSocketAddress(Ipv4Address::GetAny(), port)));       
                    sh.Install(host[h][i].Get(j));
                }
        }
	}
	std::cout << "Finished creating BulkSend traffic"<<"\n";


// schedule progress reporting 
    if (progress_period != 0) {
        Simulator::Schedule (MicroSeconds (progress_period), &ProgressTracking, progress_period, sim_duration, progress_period, alpha, use_pbs);
	}

//=========== Start the simulation ===========//
//

	std::cout << "Start Simulation.. "<<"\n";

// Populate Routing Tables
//
  	Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

// Calculate Throughput using Flowmonitor
//
  	FlowMonitorHelper flowmon;
	NodeContainer smallFlowNodes = NodeContainer();
	smallFlowNodes.Add(host[src_pod][src_edge].Get(src_host));
	smallFlowNodes.Add(host[target_pod][target_edge].Get(target_host));
	Ptr<FlowMonitor> monitor = flowmon.Install(smallFlowNodes);
// Add Tracing to Track Egress Traffic
//
	AsciiTraceHelper ascii;
	//p2p_edgeToAgg.EnableAscii( ascii.CreateFileStream (output_directory + tag + ".load.tr"), networkLoadTracer );

// Run simulation.
//
  	NS_LOG_INFO ("Run Simulation.");
	Simulator::Stop (MicroSeconds(sim_duration));

// Start Simulation
  	Simulator::Run ();

  	monitor->CheckForLostPackets ();

  	monitor->SerializeToXmlFile(filename, true, true);

	std::cout << "Simulation finished "<<"\n";

  	Simulator::Destroy ();
  	NS_LOG_INFO ("Done.");

// Print Results stored in PbsPacketFilters
//
	ofstream pbs_stats;
	ofstream pbs_egress;
	ofstream pbs_packets;
	ofstream pbs_prio;
	ofstream pbs_rawprio;
	ofstream pbs_categories;
	pbs_stats.open (output_directory + tag + ".stats");
	pbs_egress.open (output_directory + tag + ".egress");
	pbs_packets.open (output_directory + tag + ".packets");
	pbs_prio.open (output_directory + tag + ".prio");
	pbs_rawprio.open (output_directory + tag + ".rawprio");
	pbs_categories.open (output_directory + tag + ".categories");

	pbs_stats << "\n*** QueueDisc statistics (Host) ***\n";
	for (h = 0; h < num_pod; h++) {
		for (i = 0; i < num_edge; i++) {
			for (uint32_t k = 0; k < qdiscHost[h][i].GetN(); k++)
			{
				pbs_stats << "Host[" << h << "][" << i << "][" << k << "]\n";
				Ptr<QueueDisc> q = qdiscHost[h][i].Get (k);
				PbsPacketFilter *pf = dynamic_cast<PbsPacketFilter*>( PeekPointer (q->GetPacketFilter (0)) );
				pf->PrintStats (pbs_stats);
				pf->StreamToCsv (pbs_prio);
				pf->StreamPacketsToCsv (pbs_packets);
				pf->StreamRawPrioToCsv (pbs_rawprio);

				map<uint64_t, uint64_t> loadAtTime = pf->PeekLoadAtTime ();
				for (auto it = loadAtTime.begin(); it != loadAtTime.end(); ++it)
				{
					pbs_egress << it->first << "," << it->second << ",10" << rateUnits << "\n";
				}
			}
		}
	}
	

	pbs_stats << "\n*** QueueDisc statistics (EdgeDown) ***\n";
	for (h = 0; h < num_pod; h++) {
		for (i = 0; i < num_edge; i++) {
			for (uint32_t k = 0; k < qdiscEdgeDown[h][i].GetN(); k++)
			{
				pbs_stats << "EdgeDown[" << h << "][" << i << "]\n";
				Ptr<QueueDisc> q = qdiscEdgeDown[h][i].Get (k);
				PbsSwitchPacketFilter *pf = dynamic_cast<PbsSwitchPacketFilter*>( PeekPointer (q->GetPacketFilter (0)) );
				pf->PrintStats (pbs_stats);
			}
		}
	}

	pbs_stats << "\n*** QueueDisc statistics (EdgeUp) ***\n";
	for (h = 0; h < num_pod; h++) {
		for (i = 0; i < num_agg; i++) {
			for (int k = 0; k < num_edge; k++)
			{
				pbs_stats << "EdgeUp[" << h << "][" << i << "][" << k << "]\n";
				Ptr<QueueDisc> q = qdiscEdgeUp[h][i][k].Get (0);
				PbsSwitchPacketFilter *pf = dynamic_cast<PbsSwitchPacketFilter*>( PeekPointer (q->GetPacketFilter (0)) );
				pf->PrintStats (pbs_stats);
			}
		}
	}

	// To calculate Network load: snapshot total egress from every switch every nanosecond
	// To get "total egress" we look at the packets enqueued to 1 group of packet filters
	// - agg - will see egress sent from agg->edges, which is limited by the max BsBw
	pbs_egress << "#<Time Bucket>,<Total Egress Bytes-Per-Second>,<Link Rate>\n";

	pbs_stats << "\n*** QueueDisc statistics (Agg) ***\n";
	pbs_categories << "flow_id,total_bytes,p0_bytes,p1_bytes,p2_bytes,p3_bytes,p4_bytes,p5_bytes,p6_bytes,p7_bytes,\n";
	for (h = 0; h < num_pod; h++) {
		for (i = 0; i < num_agg; i++) {
			for (int k = 0; k < num_edge; k++)
			{
				pbs_stats << "Agg[" << h << "][" << i << "][" << k << "]\n";
				Ptr<QueueDisc> q = qdiscAgg[h][i][k].Get (0);
				PbsSwitchPacketFilter *pf = dynamic_cast<PbsSwitchPacketFilter*>( PeekPointer (q->GetPacketFilter (0)) );
				pf->PrintStats (pbs_stats);

				pf->PrintFlowCategories (pbs_categories);

				//// for every down-facing aggregate-switch filter, for every nanosecond in which that filter is processing a packet
				//// record the egress in total bytes from that filter
				//map<uint64_t, uint64_t> loadAtTime = pf->PeekLoadAtTime ();
				//for (auto it = loadAtTime.begin(); it != loadAtTime.end(); ++it)
				//{
				//	pbs_egress << it->first << "," << it->second << ",40" << rateUnits << "\n";
				//}
			}
		}
	}


	pbs_stats.close();
	pbs_egress.close();
	pbs_packets.close();
	pbs_prio.close();
	pbs_rawprio.close();
	pbs_categories.close();

	return 0;
}






