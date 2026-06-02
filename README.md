# 🚗 VANET Traffic-Aware Routing Protocol

> **Weight-Based Routing Decision Engine vs AODV Baseline**  
> Full simulation pipeline: SUMO mobility → Python metrics → Streamlit dashboard

---

## 📁 Project Structure

```
vanet_project/
├── vanet_simulation.py   # Core simulation engine (all 6 metrics)
├── generate_plots.py     # Publication-quality graph generator (10 plots)
├── app.py                # Streamlit dashboard (5 interactive pages)
├── run.sh                # One-shot launcher (install → simulate → plot → dashboard)
├── requirements.txt
│
├── bridge/
│   └── traci_manager.py  # TraCI bridge: SUMO ↔ Python metric extractor
│
├── ns3_scripts/
│   ├── vanet_routing.cc  # NS-3 C++ simulation (802.11p + weight-based router)
│   ├── vanet_routing.h   # Weight constants header
│   └── output/           # NS-3 XML animation & results
│
├── sumo/
│   ├── grid.net.xml      # 4×4 km urban grid road network
│   ├── sumo.cfg          # SUMO configuration
│   ├── routes_low.rou.xml    # 20-vehicle scenario
│   ├── routes_medium.rou.xml # 60-vehicle scenario
│   └── routes_high.rou.xml   # 100-vehicle scenario
│
├── results/
│   ├── low_density_stats.csv
│   ├── medium_density_stats.csv
│   ├── high_density_stats.csv
│   ├── live_stats.csv            # Dashboard feed (latest scenario)
│   ├── comparison_summary.csv    # Per-scenario aggregates
│   └── protocol_comparison_table.csv  # 6-metric summary table
│
└── plots/
    ├── 1_delay_vs_time.png
    ├── 2_pdr_vs_vehicles.png
    ├── 3_throughput_vs_density.png
    ├── 4_routing_overhead.png
    ├── 5_travel_time_vs_congestion.png
    ├── 6_congestion_heatmap.png
    ├── 7_summary_comparison.png
    ├── 8_radar_chart.png
    ├── 9_comparison_table.png
    └── 10_jitter_analysis.png
```

---

## 🏗️ Algorithm

### Weight-Based Routing Score

```
Score = (W1 × Density_Score) + (W2 × Stability) + (W3 × Distance_Score)

Where:
  W1 = 0.50  (Traffic Density – 50%)
  W2 = 0.30  (Link Stability  – 30%)
  W3 = 0.20  (Route Distance  – 20%)

Density_Score = 1.0  if 0.3 < density < 0.7  (optimal range)
              = 0.2  if density ≥ 0.7         (congested)
              = 0.1  if density < 0.3         (sparse)

Stability     = 300m / (mean_speed + 0.5)     (IEEE 802.11p range / speed)

Distance_Score = 1 / distance_km              (shorter = higher score)
```

---

## 📊 Metrics Produced

| # | Metric | Unit | Description |
|---|--------|------|-------------|
| 1 | End-to-End Delay | ms | Packet travel time src→dst |
| 2 | PDR | % | % of packets successfully delivered |
| 3 | Throughput | Mbps | Data rate of successful transmissions |
| 4 | Routing Overhead | packets | Control traffic per step |
| 5 | Travel Time | s | Vehicle transit time across grid |
| 6 | Congestion Index | 0–1 | Load distribution on road segments |

### Expected Results vs AODV

| Parameter | Traditional (AODV) | Our Protocol |
|-----------|-------------------|--------------|
| Delay | High | **Lower** (~40% reduction) |
| PDR | Moderate | **High** (>90%) |
| Travel Time | Longer | **Shorter** (~30% reduction) |
| Congestion | Uneven | **Balanced** |

---

## 🚀 How to Run (WSL Ubuntu)

### Quick Start (Recommended)

```bash
cd vanet_project
bash run.sh
```

This will:
1. Install all Python dependencies
2. Run all three scenarios (Low / Medium / High)
3. Generate all 10 plots
4. Launch the Streamlit dashboard at `http://localhost:8501`

---

### Step-by-Step (Manual)

#### 1. Install Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

#### 2. Run Simulations

```bash
# Run all three scenarios at once (no SUMO required)
python3 vanet_simulation.py --all --no-sumo

# OR run individually
python3 vanet_simulation.py --scenario low    --no-sumo
python3 vanet_simulation.py --scenario medium --no-sumo
python3 vanet_simulation.py --scenario high   --no-sumo
```

#### 3. Generate All Plots

```bash
python3 generate_plots.py
```

Saves 10 PNG files to `plots/`.

#### 4. Launch Dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

### With SUMO (Advanced)

Install SUMO on WSL Ubuntu:

```bash
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install -y sumo sumo-tools sumo-doc
echo 'export SUMO_HOME=/usr/share/sumo' >> ~/.bashrc
source ~/.bashrc
pip install traci --break-system-packages
```

Then run **without** `--no-sumo`:

```bash
python3 vanet_simulation.py --all
```

---

### NS-3 (C++ Simulation)

Compile and run the NS-3 script:

```bash
# From your ns-3 root directory:
cp vanet_project/ns3_scripts/vanet_routing.cc scratch/
cp vanet_project/ns3_scripts/vanet_routing.h  scratch/
./waf --run "vanet_routing --nVehicles=60 --simTime=100 --ourProtocol=true"

# Compare with AODV baseline:
./waf --run "vanet_routing --nVehicles=60 --simTime=100 --ourProtocol=false"
```

Results saved to `ns3_scripts/output/ns3_results.txt`.  
Animation XML: `ns3_scripts/output/vanet_anim.xml` (view with NetAnim).

---

## 🖥️ Dashboard Pages

| Page | Description |
|------|-------------|
| 🏠 Overview | Quick comparison table + project summary |
| 📡 Live Monitor | Real-time PDR / Delay / Throughput / Jitter charts (auto-refreshes) |
| 📊 Performance Graphs | Interactive tabbed charts for all 6 metrics |
| 🗺️ Congestion Map | Heatmap + animated vehicle movement |
| 📋 Comparison Table | Full numeric table + radar chart |
| 🖼️ Plot Gallery | Browse and download all 10 generated plots |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Traffic mobility | SUMO (Simulation of Urban MObility) |
| Python bridge | TraCI API |
| Network simulation | NS-3 with IEEE 802.11p (WAVE) |
| Visualisation | Streamlit + Plotly (interactive) |
| Static plots | Matplotlib |
| Data processing | Pandas + NumPy |

---

## 📞 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: streamlit` | `pip install streamlit --break-system-packages` |
| `No simulation data found` | Run `python3 vanet_simulation.py --all --no-sumo` first |
| SUMO not found | Use `--no-sumo` flag; or install SUMO (see above) |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |
| WSL display issues | Dashboard runs headless; access via browser on Windows |
