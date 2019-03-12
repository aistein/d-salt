/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
 /*
  * Copyright (c) 2015 Universita' degli Studi di Napoli Federico II
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
  * Authors: Pasquale Imputato <p.imputato@gmail.com>
  *          Stefano Avallone <stefano.avallone@unina.it>
  */

 // new netork topology
 // four nodes, send1, send2, switch, recieve
 // two senders (send1, send2) these are connected to the switch with fast (accessLink) type links
 // the switch is connected to the recieve node with the limited priority queue type link
 
 // STATUS - working currently both flows send data but piority doesnt seem to have an effect.  

 // TODO
 // create a wrapper class of the onoffapplication to cause priority to be updated every time the application is started.  

 
 #include "ns3/core-module.h"
 #include "ns3/network-module.h"
 #include "ns3/internet-module.h"
 #include "ns3/point-to-point-module.h"
 #include "ns3/applications-module.h"
 #include "ns3/internet-apps-module.h"
 #include "ns3/traffic-control-module.h"
 #include "ns3/flow-monitor-module.h"
 
 using namespace ns3;
 
 NS_LOG_COMPONENT_DEFINE ("BenchmarkQueueDiscs");
 
 void
 BytesInQueueTrace (Ptr<OutputStreamWrapper> stream, uint32_t oldVal, uint32_t newVal)
 {
   *stream->GetStream () << Simulator::Now ().GetSeconds () << " " << newVal << std::endl;
 }
 
 static void
 GoodputSampling (std::string fileName, ApplicationContainer app, Ptr<OutputStreamWrapper> stream, float period, std::string message)
 {
   Simulator::Schedule (Seconds (period), &GoodputSampling, fileName, app, stream, period, message);
   double goodput;
   uint64_t totalPackets = DynamicCast<PacketSink> (app.Get (0))->GetTotalRx ();
   goodput = totalPackets * 8 / (Simulator::Now ().GetSeconds () * 1024); // Kbit/s
   *stream->GetStream () << Simulator::Now ().GetSeconds () << " " << goodput << std::endl;
   std::cout << message << " " << Simulator::Now ().GetSeconds () << " " << goodput << std::endl;
 }

 void
 EstablishPrioirty(ApplicationContainer app, uint8_t priority, std::string message) 
 {
   Ptr<Application> app_plain = app.Get(0);
   Ptr<OnOffApplication> app_only = DynamicCast <OnOffApplication> (app_plain);
   Ptr<Socket> send_socket = app_only->GetSocket();
   std::cout << message << " set to priority " << std::to_string(priority) << std::endl;
   if(!send_socket) {
       // null pointer 
       std::cout << "ERROR null ptr detected! Unable to set priority" << std::endl;
   } else {
       send_socket->SetPriority(priority);
   }
 }
 
 static void PingRtt (std::string context, Time rtt)
 {
    //std::cout << context << "=" << rtt.GetMilliSeconds () << " ms" << std::endl;
 }
 
 int main (int argc, char *argv[])
 {
   std::string queueDiscType = "PfifoFast";
   //uint32_t queueDiscSize = 1000;
   uint32_t netdevicesQueueSize = 50;
 
   std::string flowsDatarate = "100Mbps";
   uint32_t flowsPacketsSize = 1000;
 
   float startTime = 0.1f; // in s
   float simDuration = 20;
   float samplingPeriod = 1;
 
   float stopTime = startTime + simDuration;
 
   // Create nodes
   NodeContainer tx1, tx2, sw, rx;
   tx1.Create (1);
   tx2.Create (1);
   sw.Create (1);
   rx.Create (1);
 
   // Create and configure access link and bottleneck link
   std::string bandwidth = "100Mbps";
   std::string delay = "0.1ms";

   PointToPointHelper accessLink;
   accessLink.SetDeviceAttribute ("DataRate", StringValue (bandwidth));
   accessLink.SetChannelAttribute ("Delay", StringValue (delay));
 
   PointToPointHelper bottleneckLink;
   bottleneckLink.SetDeviceAttribute ("DataRate", StringValue (bandwidth));  
   bottleneckLink.SetChannelAttribute ("Delay", StringValue (delay));        
 
   InternetStackHelper stack;
   stack.InstallAll ();
 
   // Access link traffic control configuration
   TrafficControlHelper tchPfifoFastAccess;
   tchPfifoFastAccess.SetRootQueueDisc ("ns3::PfifoFastQueueDisc", "MaxSize", StringValue ("1000p"));
 
   // Bottleneck link traffic control configuration
   TrafficControlHelper tchBottleneck;
   // Configure the prioirity queue at the link point
   uint16_t handle = tchBottleneck.SetRootQueueDisc ("ns3::PrioQueueDisc", "Priomap",
                                                     StringValue ("0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1"));
   TrafficControlHelper::ClassIdList cid = tchBottleneck.AddQueueDiscClasses (handle, 2, "ns3::QueueDiscClass");
   tchBottleneck.AddChildQueueDisc (handle, cid[0], "ns3::FifoQueueDisc");
   tchBottleneck.AddChildQueueDisc (handle, cid[1], "ns3::FifoQueueDisc");
 
   Config::SetDefault ("ns3::QueueBase::MaxSize", StringValue ("100p"));
 
   NetDeviceContainer devicesAccessLink = accessLink.Install (tx1.Get (0), sw.Get (0));
   tchPfifoFastAccess.Install (devicesAccessLink);
   Ipv4AddressHelper address;
   address.SetBase ("192.168.0.0", "255.255.255.0");
   address.NewNetwork ();
   Ipv4InterfaceContainer interfaces_tx1_accessLink = address.Assign (devicesAccessLink);
   
   devicesAccessLink = accessLink.Install (tx2.Get (0), sw.Get (0));
   tchPfifoFastAccess.Install (devicesAccessLink);;
   address.NewNetwork ();
   Ipv4InterfaceContainer interfaces_tx2_accessLink = address.Assign (devicesAccessLink);
   
 
   Config::SetDefault ("ns3::QueueBase::MaxSize", StringValue (std::to_string (netdevicesQueueSize) + "p"));
 
   // connect switch to reciever by priority queue link
   NetDeviceContainer devicesBottleneckLink = bottleneckLink.Install (sw.Get (0), rx.Get (0));
   QueueDiscContainer qdiscs;
   qdiscs = tchBottleneck.Install (devicesBottleneckLink);
   address.NewNetwork ();
   Ipv4InterfaceContainer interfacesDownlink = address.Assign (devicesBottleneckLink);
 
   Ptr<NetDeviceQueueInterface> interface = devicesBottleneckLink.Get (0)->GetObject<NetDeviceQueueInterface> ();
   Ptr<NetDeviceQueue> queueInterface = interface->GetTxQueue (0);
   Ptr<DynamicQueueLimits> queueLimits = StaticCast<DynamicQueueLimits> (queueInterface->GetQueueLimits ());
 
   AsciiTraceHelper ascii;
   Ptr<Queue<Packet> > queue = StaticCast<PointToPointNetDevice> (devicesBottleneckLink.Get (0))->GetQueue ();
   Ptr<OutputStreamWrapper> streamBytesInQueue = ascii.CreateFileStream (queueDiscType + "-bytesInQueue.txt");
   queue->TraceConnectWithoutContext ("BytesInQueue",MakeBoundCallback (&BytesInQueueTrace, streamBytesInQueue));
 
   //get interfaces for decleration in applications
   Ipv4InterfaceContainer tx1_interface, tx2_interface;
   tx1_interface.Add (interfaces_tx1_accessLink.Get (0));
   tx2_interface.Add (interfaces_tx2_accessLink.Get (0));
 
   Ipv4InterfaceContainer rxInterface;
   rxInterface.Add (interfacesDownlink.Get (1));
 
   Ipv4GlobalRoutingHelper::PopulateRoutingTables ();
 
   Config::SetDefault ("ns3::TcpSocket::SegmentSize", UintegerValue (flowsPacketsSize));

   // Flows configuration
   // Bidirectional TCP streams with ping like flent tcp_bidirectional test.
   uint16_t port = 56;
   ApplicationContainer send_1_app, send_2_app, priorityTesterApp_rx1, priorityTesterApp_rx2;
   // Configure and install priority tester flow
   // config the rx packet sink
   Address addrPrio_rx1 (InetSocketAddress (Ipv4Address::GetAny (), port));
   PacketSinkHelper sinkHelperUp_rx1 ("ns3::TcpSocketFactory", addrPrio_rx1);
   sinkHelperUp_rx1.SetAttribute ("Protocol", TypeIdValue (TcpSocketFactory::GetTypeId ()));
   priorityTesterApp_rx1.Add (sinkHelperUp_rx1.Install (rx));
   
   // configure application for generating traffic from tx hosts
   // config application for sender 1
   InetSocketAddress socketAddressUp = InetSocketAddress (rxInterface.GetAddress (0), port);
   OnOffHelper onOffHelperUp ("ns3::TcpSocketFactory", Address ());
   onOffHelperUp.SetAttribute ("Remote", AddressValue (socketAddressUp));
   onOffHelperUp.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
   onOffHelperUp.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
   onOffHelperUp.SetAttribute ("PacketSize", UintegerValue (flowsPacketsSize));
   onOffHelperUp.SetAttribute ("DataRate", StringValue (flowsDatarate));
   ApplicationContainer tx1_send_app = onOffHelperUp.Install (tx1);
   send_1_app.Add (tx1_send_app);


   // config application for sender 2
   port++;
   Address addrPrio_rx2 (InetSocketAddress (Ipv4Address::GetAny (), port));
   PacketSinkHelper sinkHelperUp_rx2 ("ns3::TcpSocketFactory", addrPrio_rx2);
   sinkHelperUp_rx2.SetAttribute ("Protocol", TypeIdValue (TcpSocketFactory::GetTypeId ()));
   priorityTesterApp_rx2.Add (sinkHelperUp_rx2.Install (rx));

   InetSocketAddress socketAddressUp_rx2 = InetSocketAddress (rxInterface.GetAddress (0), port);
   OnOffHelper onOffHelperUp_rx2 ("ns3::TcpSocketFactory", Address ());
   onOffHelperUp_rx2.SetAttribute ("Remote", AddressValue (socketAddressUp_rx2));
   onOffHelperUp_rx2.SetAttribute ("OnTime", StringValue ("ns3::ConstantRandomVariable[Constant=1]"));
   onOffHelperUp_rx2.SetAttribute ("OffTime", StringValue ("ns3::ConstantRandomVariable[Constant=0]"));
   onOffHelperUp_rx2.SetAttribute ("PacketSize", UintegerValue (flowsPacketsSize));
   onOffHelperUp_rx2.SetAttribute ("DataRate", StringValue (flowsDatarate));
   ApplicationContainer tx2_send_app = onOffHelperUp_rx2.Install (tx2);
   send_2_app.Add (tx2_send_app);
 
   // Configure and install ping
   V4PingHelper ping = V4PingHelper (rxInterface.GetAddress (0));
   ping.Install (sw);
 
   Config::Connect ("/NodeList/*/ApplicationList/*/$ns3::V4Ping/Rtt", MakeCallback (&PingRtt));
 
   priorityTesterApp_rx1.Start (Seconds (0));
   priorityTesterApp_rx1.Stop (Seconds (stopTime));
   
   priorityTesterApp_rx2.Start (Seconds (0));
   priorityTesterApp_rx2.Stop (Seconds (stopTime));
 
   send_1_app.Start (Seconds (0 + 0.1));
   Simulator::Schedule (Seconds (0 + 0.2), &EstablishPrioirty, tx1_send_app, 1, "tx1");
   send_1_app.Stop (Seconds (stopTime - 5));

   send_2_app.Start (Seconds (0 + stopTime/2));
   Simulator::Schedule (Seconds (0 + stopTime/2 + 0.1), &EstablishPrioirty, tx2_send_app, 0, "tx2");
   send_2_app.Stop (Seconds (stopTime - 1.1));


   Ptr<OutputStreamWrapper> tx1_GoodputStream = ascii.CreateFileStream ("tx1-rcvRate.txt");
   Simulator::Schedule (Seconds (samplingPeriod), &GoodputSampling, "tx1-rcvRate.txt", priorityTesterApp_rx1,
                        tx1_GoodputStream, samplingPeriod, "tx1 throughput");
   Ptr<OutputStreamWrapper> tx2_GoodputStream = ascii.CreateFileStream ("tx2-rcvRate.txt");
   Simulator::Schedule (Seconds (samplingPeriod), &GoodputSampling, "tx2-rcvRate.txt", priorityTesterApp_rx2,
                        tx2_GoodputStream, samplingPeriod, "tx2 throughput");
 
   // Flow monitor
   Ptr<FlowMonitor> flowMonitor;
   FlowMonitorHelper flowHelper;
   flowMonitor = flowHelper.InstallAll();
 
   Simulator::Stop (Seconds (stopTime));
   Simulator::Run ();
 
   flowMonitor->SerializeToXmlFile("flowMonitor.xml", true, true);
 
   Simulator::Destroy ();
   return 0;
 }

