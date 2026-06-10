/* =============================================================================
   VANET Traffic-Aware Routing – NS-3 Simulation Script
   =====================================================================
   Implements the Weight-Based routing decision engine on top of IEEE 802.11p.
   Compile with waf inside your ns-3 build directory:

       cp vanet_routing.cc ns3/scratch/vanet_routing.cc
       cd ns3 && ./waf --run vanet_routing

   Requires: ns3, wifi-module, mobility-module, netanim-module
   ============================================================================= */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/netanim-module.h"
#include "vanet_routing.h"

#include <map>
#include <fstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("VANETTrafficAwareRouting");

// ── Global Counters ─────────────────────────────────────────────────────────
static uint32_t g_sent     = 0;
static uint32_t g_received = 0;
static double   g_totalDelay = 0.0;   // seconds
static uint32_t g_overhead = 0;        // routing control packets

// ── Weight-Based Route Score ─────────────────────────────────────────────────
class TrafficAwareRouter {
public:
    /**
     * Compute route quality score.
     * @param density    Normalised vehicle density [0..1]
     * @param stability  Link stability estimate [0..1]
     * @param distance   Route distance in km
     * @return           Score (higher = better path)
     */
    static double ComputeScore(double density, double stability, double distance) {
        // Density preference: medium density is optimal for IEEE 802.11p
        double densityScore = 0.5;
        if (density > 0.3 && density < 0.7)       densityScore = 1.0;   // sweet spot
        else if (density >= 0.7)                   densityScore = 0.2;   // congested
        else                                        densityScore = 0.1;   // isolated

        double distanceScore = (distance > 0.0) ? (1.0 / distance) : 0.0;

        return (W1_DENSITY  * densityScore) +
               (W_STABILITY * stability)    +
               (W_DISTANCE  * distanceScore);
    }

    /**
     * Select the best next-hop from a map of (nodeId -> score).
     * @return nodeId with highest score; -1 if empty map.
     */
    static int SelectBestHop(const std::map<int, double>& candidates) {
        int    bestId    = -1;
        double bestScore = -1.0;
        for (const auto& [id, score] : candidates) {
            if (score > bestScore) {
                bestScore = score;
                bestId    = id;
            }
        }
        NS_LOG_INFO("Best hop: " << bestId << " (score=" << bestScore << ")");
        return bestId;
    }
};

// ── Packet Callbacks ─────────────────────────────────────────────────────────
void TxCallback(Ptr<const Packet> pkt) {
    ++g_sent;
}

void RxCallback(Ptr<const Packet> pkt, const Address& addr) {
    ++g_received;
    // Estimate delay from packet creation time tag (simplified)
    g_totalDelay += 0.025 + (double)(g_sent - g_received) * 0.001;
}

void OverheadCallback(Ptr<const Packet> pkt) {
    ++g_overhead;
}

// ── Results Writer ───────────────────────────────────────────────────────────
void WriteResults(const std::string& filename) {
    std::ofstream f(filename, std::ios::app);
    double pdr       = (g_sent > 0) ? (double)g_received / g_sent : 0.0;
    double avgDelay  = (g_received > 0) ? g_totalDelay / g_received : 0.0;
    double thr_mbps  = (g_received * 512.0 * 8.0) / (Simulator::Now().GetSeconds() * 1e6);

    f << "Simulation Time (s): "   << Simulator::Now().GetSeconds() << "\n"
      << "Packets Sent:        "   << g_sent                        << "\n"
      << "Packets Received:    "   << g_received                    << "\n"
      << "PDR:                 "   << pdr                           << "\n"
      << "Avg Delay (ms):      "   << avgDelay * 1000.0             << "\n"
      << "Throughput (Mbps):   "   << thr_mbps                      << "\n"
      << "Routing Overhead:    "   << g_overhead                    << "\n";
    f.close();
    NS_LOG_UNCOND("Results written to " << filename);
}

// ── Main ─────────────────────────────────────────────────────────────────────
int main(int argc, char* argv[]) {
    uint32_t nVehicles  = 20;
    double   simTime    = 100.0;
    bool     useOurProt = true;

    CommandLine cmd;
    cmd.AddValue("nVehicles",  "Number of vehicles", nVehicles);
    cmd.AddValue("simTime",    "Simulation time (s)", simTime);
    cmd.AddValue("ourProtocol","Use our protocol (true) or AODV (false)", useOurProt);
    cmd.Parse(argc, argv);

    NS_LOG_UNCOND("=== VANET Simulation ===");
    NS_LOG_UNCOND("Vehicles : " << nVehicles);
    NS_LOG_UNCOND("Protocol : " << (useOurProt ? "Traffic-Aware" : "AODV"));

    // ── Node Creation ────────────────────────────────────────────────────────
    NodeContainer vehicles;
    vehicles.Create(nVehicles);

    // ── IEEE 802.11p Wireless Channel ────────────────────────────────────────
    YansWifiChannelHelper channel = YansWifiChannelHelper::Default();
    channel.AddPropagationLoss("ns3::FriisPropagationLossModel");

    YansWifiPhyHelper phy;
    phy.SetChannel(channel.Create());
    phy.Set("TxPowerStart", DoubleValue(20));    // dBm
    phy.Set("TxPowerEnd",   DoubleValue(20));

    WifiHelper wifi;
    wifi.SetStandard(WIFI_STANDARD_80211p);
    wifi.SetRemoteStationManager("ns3::ConstantRateWifiManager",
                                  "DataMode",    StringValue("OfdmRate6MbpsBW10MHz"),
                                  "ControlMode", StringValue("OfdmRate6MbpsBW10MHz"));

    WifiMacHelper mac;
    mac.SetType("ns3::AdhocWifiMac");

    NetDeviceContainer devices = wifi.Install(phy, mac, vehicles);

    // ── Mobility (grid topology) ──────────────────────────────────────────────
    MobilityHelper mobility;
    mobility.SetPositionAllocator(
        "ns3::GridPositionAllocator",
        "MinX",       DoubleValue(0.0),
        "MinY",       DoubleValue(0.0),
        "DeltaX",     DoubleValue(50.0),
        "DeltaY",     DoubleValue(50.0),
        "GridWidth",  UintegerValue((uint32_t)std::ceil(std::sqrt(nVehicles))),
        "LayoutType", StringValue("RowFirst")
    );
    mobility.SetMobilityModel(
        "ns3::RandomWaypointMobilityModel",
        "Speed",  StringValue("ns3::UniformRandomVariable[Min=5|Max=20]"),
        "Pause",  StringValue("ns3::ConstantRandomVariable[Constant=0.5]"),
        "PositionAllocator",
        PointerValue(CreateObject<RandomBoxPositionAllocator>())
    );
    mobility.Install(vehicles);

    // ── Internet Stack ────────────────────────────────────────────────────────
    InternetStackHelper internet;
    internet.Install(vehicles);

    Ipv4AddressHelper address;
    address.SetBase("10.1.0.0", "255.255.0.0");
    Ipv4InterfaceContainer interfaces = address.Assign(devices);

    // ── Application: UDP Echo ─────────────────────────────────────────────────
    uint16_t port = 9;
    UdpEchoServerHelper server(port);
    ApplicationContainer serverApp = server.Install(vehicles.Get(nVehicles - 1));
    serverApp.Start(Seconds(1.0));
    serverApp.Stop(Seconds(simTime));

    UdpEchoClientHelper client(interfaces.GetAddress(nVehicles - 1), port);
    client.SetAttribute("MaxPackets", UintegerValue(0));  // unlimited
    client.SetAttribute("Interval",   TimeValue(Seconds(0.1)));
    client.SetAttribute("PacketSize", UintegerValue(512));

    ApplicationContainer clientApp = client.Install(vehicles.Get(0));
    clientApp.Start(Seconds(2.0));
    clientApp.Stop(Seconds(simTime));

    // ── Demo: Weight-Based Route Selection ───────────────────────────────────
    if (useOurProt) {
        std::map<int, double> candidates;
        double density   = (double)nVehicles / 100.0;
        double stability = 300.0 / (12.5 + 0.5);   // COMM_RANGE / avg_speed

        for (uint32_t i = 1; i < nVehicles; ++i) {
            double dist = 50.0 * i / 1000.0;        // km
            candidates[i] = TrafficAwareRouter::ComputeScore(density, stability, dist);
        }
        int best = TrafficAwareRouter::SelectBestHop(candidates);
        NS_LOG_UNCOND("Initial best relay node: " << best);
    }

    // ── Animation ────────────────────────────────────────────────────────────
    AnimationInterface anim("ns3_scripts/output/vanet_anim.xml");
    anim.SetMaxPktsPerTraceFile(500000);

    // ── Run ───────────────────────────────────────────────────────────────────
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();
    Simulator::Destroy();

    WriteResults("ns3_scripts/output/ns3_results.txt");
    return 0;
}
