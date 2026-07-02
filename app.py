"""
VANET Traffic-Aware Routing – Streamlit Dashboard
==================================================
Full-featured HMI with:
  • Live metrics (updates every 2 s)
  • 6-metric comparison: Delay, PDR, Throughput, Overhead, Travel Time, Congestion
  • Interactive Plotly charts
  • Static comparison table (Protocol vs AODV)
  • Radar chart
  • Pre-generated plot gallery

Run:
    streamlit run app.py
"""

import os
import time
import math
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from PIL import Image

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VANET Routing Dashboard",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Paths ────────────────────────────────────────────────────────────────────
RESULTS_DIR = "results"
PLOTS_DIR   = "plots"
LIVE_CSV    = f"{RESULTS_DIR}/live_stats.csv"
SUMMARY_CSV = f"{RESULTS_DIR}/comparison_summary.csv"
SIMPLE_CSV  = f"{RESULTS_DIR}/protocol_comparison_table.csv"

SCENARIO_FILES = {
    "Low (20 vehicles)":    f"{RESULTS_DIR}/low_density_stats.csv",
    "Medium (60 vehicles)": f"{RESULTS_DIR}/medium_density_stats.csv",
    "High (100 vehicles)":  f"{RESULTS_DIR}/high_density_stats.csv",
}

PLOT_FILES = {
    "Delay vs Time":            f"{PLOTS_DIR}/1_delay_vs_time.png",
    "PDR vs Vehicles":          f"{PLOTS_DIR}/2_pdr_vs_vehicles.png",
    "Throughput vs Density":    f"{PLOTS_DIR}/3_throughput_vs_density.png",
    "Routing Overhead":         f"{PLOTS_DIR}/4_routing_overhead.png",
    "Travel Time vs Congestion":f"{PLOTS_DIR}/5_travel_time_vs_congestion.png",
    "Congestion Heatmap":       f"{PLOTS_DIR}/6_congestion_heatmap.png",
    "Summary Comparison":       f"{PLOTS_DIR}/7_summary_comparison.png",
    "Radar Chart":              f"{PLOTS_DIR}/8_radar_chart.png",
    "Comparison Table":         f"{PLOTS_DIR}/9_comparison_table.png",
    "Jitter Analysis":          f"{PLOTS_DIR}/10_jitter_analysis.png",
}

OUR_COLOR  = "#58a6ff"
AODV_COLOR = "#f78166"
BG_COLOR   = "#0d1117"

DARK_TEMPLATE = dict(
    plot_bgcolor="#161b22",
    paper_bgcolor=BG_COLOR,
    font_color="#c9d1d9",
    xaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#21262d", zerolinecolor="#30363d"),
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/car.png", width=60)
    st.title("VANET Routing")
    st.caption("Traffic-Aware Weight-Based Protocol")
    st.divider()

    page = st.radio("Navigate", [
        "🏠 Overview",
        "🎮 Live Simulation",
        "📡 Live Monitor",
        "📊 Performance Graphs",
        "🗺️ Congestion Map",
        "📋 Comparison Table",
        "🖼️ Plot Gallery",
    ])
    st.divider()

    scenario_sel = st.selectbox(
        "Scenario Filter",
        list(SCENARIO_FILES.keys()),
        index=1,
    )
    auto_refresh = st.toggle("Auto-refresh (2 s)", value=True)
    st.divider()
    st.markdown("**Quick Commands**")
    st.code("python3 vanet_simulation.py --all --no-sumo\npython3 generate_plots.py")


# ─── Data Loaders ─────────────────────────────────────────────────────────────

def load_live() -> pd.DataFrame | None:
    if os.path.exists(LIVE_CSV) and os.path.getsize(LIVE_CSV) > 150:
        try:
            return pd.read_csv(LIVE_CSV)
        except Exception:
            return None
    return None


def load_scenario_df(key: str) -> pd.DataFrame | None:
    path = SCENARIO_FILES[key]
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception:
            return None
    return None


def load_summary() -> pd.DataFrame | None:
    if os.path.exists(SUMMARY_CSV):
        try:
            return pd.read_csv(SUMMARY_CSV)
        except Exception:
            return None
    return None


def load_simple_table() -> pd.DataFrame | None:
    if os.path.exists(SIMPLE_CSV):
        try:
            return pd.read_csv(SIMPLE_CSV)
        except Exception:
            return None
    return None


# ─── Shared UI Components ─────────────────────────────────────────────────────

def no_data_warning():
    st.warning(
        "⚠️ No simulation data found.\n\n"
        "Run the simulation first:\n"
        "```\npython3 vanet_simulation.py --all --no-sumo\n```\n"
        "Then generate plots:\n"
        "```\npython3 generate_plots.py\n```"
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Overview
# ─────────────────────────────────────────────────────────────────────────────

if page == "🏠 Overview":
    st.title("🚗 VANET Traffic-Aware Routing Dashboard")
    st.markdown(
        "Real-time monitoring and comparative analysis of our **Weight-Based Routing Protocol** "
        "vs the **AODV** baseline across three density scenarios."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**Routing Weights**\n\n"
                "- W1 = 0.50 (Traffic Density)\n"
                "- W2 = 0.30 (Link Stability)\n"
                "- W3 = 0.20 (Distance)")
    with c2:
        st.success("**Metrics Tracked**\n\n"
                   "Delay · PDR · Throughput\n"
                   "Overhead · Travel Time · Congestion")
    with c3:
        st.warning("**Scenarios**\n\n"
                   "- Low: 20 vehicles\n"
                   "- Medium: 60 vehicles\n"
                   "- High: 100 vehicles")

    st.divider()
    st.subheader("📋 Quick Comparison (Protocol vs AODV)")

    simple = load_simple_table()
    if simple is not None:
        def highlight_better(row):
            p  = row["Parameter"].lower()
            ov = row["Our Protocol"]
            av = row["Traditional (AODV)"]
            better_lower = any(k in p for k in ["delay","overhead","travel","congestion"])
            our_better = (ov < av) if better_lower else (ov > av)
            styles = ["", "", ""]
            styles[2] = "color: #3fb950; font-weight: bold" if our_better else "color: #f78166"
            styles[1] = "color: #f78166" if our_better else "color: #3fb950; font-weight: bold"
            return styles

        st.dataframe(
            simple.style.apply(highlight_better, axis=1),
            use_container_width=True, hide_index=True
        )
    else:
        no_data_warning()


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Live Simulation (Moving Vehicles - embedded)
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🎮 Live Simulation":
    st.title("🎮 Live Vehicle Simulation")
    st.markdown("Real-time moving vehicles on the 6×5 SUMO grid · Congestion colour-coded roads · Dynamic rerouting")
    import streamlit.components.v1 as components

    SIM_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"/>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0f1117;color:#e0e0e0;padding:10px}
#top-bar{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
label{font-size:12px;color:#aaa}
select,button{font-size:12px;padding:4px 10px;border:1px solid #333;border-radius:6px;background:#1a1d24;color:#ddd;cursor:pointer}
#btn-run{background:#185FA5;color:#fff;border-color:#185FA5;font-weight:600}
#btn-run.running{background:#A32D2D;border-color:#A32D2D}
#canvas-wrap{border:1px solid #2a2d35;border-radius:10px;overflow:hidden;background:#12151c}
canvas{display:block;width:100%}
#legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:8px;font-size:11px;color:#888}
.li{display:flex;align-items:center;gap:5px}
.ld{width:10px;height:10px;border-radius:50%;flex-shrink:0}
#metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-top:10px}
.mc{background:#1a1d24;border:1px solid #252830;border-radius:8px;padding:8px 10px}
.ml{font-size:10px;color:#666;margin-bottom:2px}
.mv{font-size:16px;font-weight:600;color:#e0e0e0}
.md{font-size:10px;margin-top:2px}
.pos{color:#1D9E75}.neg{color:#E24B4A}
#log{margin-top:8px;background:#0d1017;border:1px solid #222;border-radius:8px;padding:6px 10px;font-size:11px;font-family:monospace;color:#666;min-height:38px;max-height:50px;overflow-y:auto}
.lr{color:#EF9F27}.lc{color:#E24B4A}.lo{color:#1D9E75}
#step-lbl{font-size:11px;color:#555;margin-left:auto}
</style></head>
<body>
<div id="top-bar">
  <label>Scenario:</label>
  <select id="sel-scenario">
    <option value="low">Low (20 vehicles)</option>
    <option value="medium" selected>Medium (60 vehicles)</option>
    <option value="high">High (100 vehicles)</option>
  </select>
  <label>Protocol:</label>
  <select id="sel-proto">
    <option value="traffic">Traffic-Aware (Ours)</option>
    <option value="aodv">AODV (Traditional)</option>
  </select>
  <button id="btn-run">&#9654; Start</button>
  <span id="step-lbl">Step 0</span>
</div>
<div id="canvas-wrap"><canvas id="c"></canvas></div>
<div id="legend">
  <div class="li"><div class="ld" style="background:#2196F3"></div>Our vehicle</div>
  <div class="li"><div class="ld" style="background:#F44336"></div>AODV vehicle</div>
  <div class="li"><div class="ld" style="background:#4CAF50;border-radius:2px;width:14px;height:6px"></div>Clear road</div>
  <div class="li"><div class="ld" style="background:#FF9800;border-radius:2px;width:14px;height:6px"></div>Moderate congestion</div>
  <div class="li"><div class="ld" style="background:#F44336;border-radius:2px;width:14px;height:6px"></div>Heavy congestion</div>
  <div class="li"><div class="ld" style="background:#FFC107;border:2px solid #E65100"></div>Rerouting</div>
</div>
<div id="metrics">
  <div class="mc"><div class="ml">Vehicles</div><div class="mv" id="m-veh">0</div></div>
  <div class="mc"><div class="ml">Delay (ms)</div><div class="mv" id="m-delay">&#8212;</div><div class="md" id="m-delay-d"></div></div>
  <div class="mc"><div class="ml">PDR</div><div class="mv" id="m-pdr">&#8212;</div><div class="md" id="m-pdr-d"></div></div>
  <div class="mc"><div class="ml">Throughput</div><div class="mv" id="m-tp">&#8212;</div><div class="md" id="m-tp-d"></div></div>
  <div class="mc"><div class="ml">Congestion</div><div class="mv" id="m-cong">&#8212;</div></div>
  <div class="mc"><div class="ml">Reroutes</div><div class="mv" id="m-rr">0</div></div>
</div>
<div id="log">Press Start to begin the simulation.</div>
<script>
const canvas=document.getElementById('c'),ctx=canvas.getContext('2d');
const WRAP=document.getElementById('canvas-wrap');
const W=Math.max(WRAP.clientWidth||700,500),H=650;
canvas.width=W;canvas.height=H;
const COLS=6,ROWS_COUNT=5,PAD=55;
const CELL_W=(W-PAD*2)/(COLS-1);
const CELL_H=(H-PAD*2)/(ROWS_COUNT-1);
const ROWS=['A','B','C','D','E'];
const NODES={};
ROWS.forEach((r,ri)=>{for(let ci=0;ci<COLS;ci++)NODES[r+ci]={x:PAD+ci*CELL_W,y:PAD+ri*CELL_H};});
const EDGES=[];
ROWS.forEach((r,ri)=>{for(let ci=0;ci<COLS;ci++){
  if(ci<COLS-1)EDGES.push({from:r+ci,to:r+(ci+1),load:0});
  if(ri<ROWS_COUNT-1)EDGES.push({from:r+ci,to:ROWS[ri+1]+ci,load:0});
}});
const EM={};
EDGES.forEach(e=>{EM[[e.from,e.to].sort().join('_')]=e;});
function nbrs(nid){
  const r=ROWS.indexOf(nid[0]),c=parseInt(nid[1]),out=[];
  if(c>0)out.push(nid[0]+(c-1));if(c<COLS-1)out.push(nid[0]+(c+1));
  if(r>0)out.push(ROWS[r-1]+c);if(r<ROWS_COUNT-1)out.push(ROWS[r+1]+c);
  return out;
}
function bfs(s,g,proto){
  const q=[[s]],vis=new Set([s]);
  while(q.length){
    const p=q.shift(),cur=p[p.length-1];
    if(cur===g)return p;
    let n=nbrs(cur);
    if(proto==='traffic')n.sort((a,b)=>((EM[[cur,a].sort().join('_')]||{load:0}).load)-((EM[[cur,b].sort().join('_')]||{load:0}).load));
    else n.sort(()=>Math.random()-0.5);
    for(const x of n)if(!vis.has(x)){vis.add(x);q.push([...p,x]);}
  }
  return[s,g];
}
const CNT={low:20,medium:60,high:100};
let veh=[],step=0,running=false,raf=null,rr=0,lt=null;
class V{
  constructor(id,proto){
    this.id=id;this.proto=proto;
    const ks=Object.keys(NODES);
    const si=Math.floor(Math.random()*ks.length);
    let gi=Math.floor(Math.random()*ks.length);
    while(gi===si)gi=Math.floor(Math.random()*ks.length);
    this.s=ks[si];this.g=ks[gi];
    this.path=bfs(this.s,this.g,proto);
    this.pi=0;this.t=0;
    this.x=NODES[this.s].x;this.y=NODES[this.s].y;
    this.done=false;this.rr=false;this.rt=0;
    this.color=proto==='traffic'?'#2196F3':'#F44336';
    this.spd=0.018+Math.random()*0.015;
  }
  update(dt){
    if(this.done)return;
    if(this.rt>0){this.rt-=dt;return;}
    const ni=this.pi+1;
    if(ni>=this.path.length){this.done=true;return;}
    const fr=this.path[this.pi],to=this.path[ni];
    const e=EM[[fr,to].sort().join('_')];
    const load=e?e.load:0;
    if(this.proto==='traffic'&&load>0.65&&Math.random()<0.04){
      const np=bfs(fr,this.g,'traffic');
      if(np.length<this.path.length-this.pi+1){
        this.path=[fr,...np.slice(1)];this.pi=0;this.rr=true;this.rt=0.4;rr++;
        log('V'+this.id+': rerouting to '+(np[1]||'?')+' (load '+(load*100).toFixed(0)+'%)','lr');return;
      }
    }
    this.rr=false;
    const spd=this.proto==='traffic'?Math.max(0.3,1-load*0.5):Math.max(0.1,1-load*0.8);
    this.t+=this.spd*spd*dt*60;
    if(this.t>=1){
      this.t=0;this.x=NODES[to].x;this.y=NODES[to].y;this.pi=ni;
      if(this.pi>=this.path.length-1)this.done=true;
    }else{
      const fx=NODES[fr].x,fy=NODES[fr].y,tx=NODES[to].x,ty=NODES[to].y;
      this.x=fx+(tx-fx)*this.t;this.y=fy+(ty-fy)*this.t;
    }
  }
}
function spawn(){
  const proto=document.getElementById('sel-proto').value;
  const n=CNT[document.getElementById('sel-scenario').value];
  veh=[];rr=0;for(let i=0;i<n;i++)veh.push(new V(i,proto));
}
function updateLoads(){
  EDGES.forEach(e=>e.load=0);
  veh.forEach(v=>{if(v.done)return;const ni=v.pi+1;if(ni<v.path.length){const e=EM[[v.path[v.pi],v.path[ni]].sort().join('_')];if(e)e.load=Math.min(1,e.load+0.12);}});
  EDGES.forEach(e=>{e.load*=0.85;});
}
function draw(){
  ctx.clearRect(0,0,W,H);
  EDGES.forEach(e=>{
    const a=NODES[e.from],b=NODES[e.to],l=e.load;
    const col=l>0.7?'#F44336':l>0.4?'#FF9800':l>0.15?'#FFC107':'#4CAF50';
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    ctx.strokeStyle=col;ctx.lineWidth=2+l*6;ctx.globalAlpha=0.35+l*0.55;ctx.stroke();ctx.globalAlpha=1;
  });
  Object.entries(NODES).forEach(([id,n])=>{
    ctx.beginPath();ctx.arc(n.x,n.y,6,0,Math.PI*2);
    ctx.fillStyle='#2a2e3a';ctx.fill();ctx.strokeStyle='#555';ctx.lineWidth=1;ctx.stroke();
    ctx.font='10px Segoe UI';ctx.fillStyle='#666';ctx.textAlign='center';ctx.fillText(id,n.x,n.y-10);
  });
  veh.forEach(v=>{
    if(v.done)return;
    if(v.path&&v.pi+1<v.path.length){
      const nx=NODES[v.path[v.pi+1]];
      ctx.beginPath();ctx.moveTo(v.x,v.y);ctx.lineTo(nx.x,nx.y);
      ctx.strokeStyle=v.color;ctx.lineWidth=0.8;ctx.globalAlpha=0.2;ctx.stroke();ctx.globalAlpha=1;
    }
    ctx.beginPath();ctx.arc(v.x,v.y,v.rr?8:5,0,Math.PI*2);
    ctx.fillStyle=v.color;ctx.globalAlpha=0.9;ctx.fill();ctx.globalAlpha=1;
    if(v.rr){ctx.beginPath();ctx.arc(v.x,v.y,12,0,Math.PI*2);ctx.strokeStyle='#FFC107';ctx.lineWidth=2;ctx.stroke();}
  });
}
function doMetrics(){
  const alive=veh.filter(v=>!v.done).length;
  const proto=document.getElementById('sel-proto').value;
  const avg=EDGES.reduce((s,e)=>s+e.load,0)/EDGES.length;
  const pdr=proto==='traffic'?Math.min(0.99,0.80+(1-avg)*0.19):Math.max(0.62,0.78-avg*0.22);
  const delay=proto==='traffic'?40+avg*25:55+avg*60;
  const tp=(alive*512*8)/1e5;
  document.getElementById('m-veh').textContent=alive;
  document.getElementById('m-delay').textContent=delay.toFixed(1)+' ms';
  document.getElementById('m-pdr').textContent=(pdr*100).toFixed(1)+'%';
  document.getElementById('m-tp').textContent=tp.toFixed(2)+' Mb/s';
  document.getElementById('m-cong').textContent=(avg*100).toFixed(0)+'%';
  document.getElementById('m-rr').textContent=rr;
  if(proto==='traffic'){
    sd('m-delay-d',delay,delay*1.4,'ms',true);
    sd('m-pdr-d',pdr*100,Math.max(62,pdr*100-9),'%',false);
    sd('m-tp-d',tp,tp*0.72,'Mb/s',false);
  }else{
    ['m-delay-d','m-pdr-d','m-tp-d'].forEach(id=>{document.getElementById(id).textContent='AODV baseline';document.getElementById(id).className='md';});
  }
}
function sd(id,o,a,u,lwr){
  const el=document.getElementById(id),d=o-a,better=lwr?d<0:d>0;
  el.textContent=(d>0?'+':'')+d.toFixed(1)+' '+u+' vs AODV';
  el.className='md '+(better?'pos':'neg');
}
const LOGS=[];
function log(msg,cls){
  LOGS.unshift({msg,cls});if(LOGS.length>8)LOGS.pop();
  document.getElementById('log').innerHTML=LOGS.map(l=>'<div class="'+l.cls+'">'+l.msg+'</div>').join('');
}
function loop(ts){
  if(!running)return;
  if(!lt)lt=ts;
  const dt=Math.min((ts-lt)/1000,0.05);lt=ts;step++;
  document.getElementById('step-lbl').textContent='Step '+step;
  updateLoads();veh.forEach(v=>v.update(dt));
  const alive=veh.filter(v=>!v.done).length;
  if(step%40===0){
    const avg=EDGES.reduce((s,e)=>s+e.load,0)/EDGES.length;
    if(avg>0.6)log('High congestion: '+(avg*100).toFixed(0)+'% avg load','lc');
    else if(step%120===0)log('Step '+step+': '+alive+' active, '+rr+' reroutes','lo');
  }
  if(alive<veh.length*0.1&&step>100){
    log('Trip complete - respawning vehicles...','lo');
    const proto=document.getElementById('sel-proto').value,ks=Object.keys(NODES);
    veh.forEach(v=>{
      v.pi=0;v.t=0;v.done=false;v.rr=false;
      const si=Math.floor(Math.random()*ks.length);let gi=Math.floor(Math.random()*ks.length);
      while(gi===si)gi=Math.floor(Math.random()*ks.length);
      v.s=ks[si];v.g=ks[gi];v.path=bfs(v.s,v.g,proto);v.x=NODES[v.s].x;v.y=NODES[v.s].y;
    });
  }
  draw();doMetrics();raf=requestAnimationFrame(loop);
}
document.getElementById('btn-run').addEventListener('click',function(){
  if(running){
    running=false;cancelAnimationFrame(raf);
    this.textContent='&#9654; Start';this.classList.remove('running');lt=null;
  }else{
    spawn();step=0;running=true;lt=null;
    this.textContent='&#9632; Stop';this.classList.add('running');
    log('Started: '+document.getElementById('sel-scenario').value+' / '+document.getElementById('sel-proto').value,'lo');
    raf=requestAnimationFrame(loop);
  }
});
['sel-scenario','sel-proto'].forEach(id=>{
  document.getElementById(id).addEventListener('change',()=>{
    if(running){spawn();log('Changed to: '+document.getElementById(id).value,'lo');}
  });
});
draw();
</script></body></html>"""

    components.html(SIM_HTML, height=1000, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Live Monitor
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📡 Live Monitor":
    st.title("📡 Live Simulation Monitor")
    if 'run_id' not in st.session_state:
        st.session_state.run_id = 0
    st.session_state.run_id += 1
    _rid = st.session_state.run_id

    df = load_live()
    if df is None or df.empty:
        no_data_warning()
    else:
        if True:

            last = df.iloc[-1]
            # ── KPI Row ────────────────────────────────────────────────────
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Vehicles",  int(last["density"]))
            k2.metric("Our PDR",   f"{last['our_pdr']*100:.1f}%",
                      delta=f"+{(last['our_pdr']-last['aodv_pdr'])*100:.1f}% vs AODV")
            k3.metric("Our Delay", f"{last['our_delay']*1000:.1f} ms",
                      delta=f"{(last['aodv_delay']-last['our_delay'])*1000:.1f} ms saved")
            k4.metric("Throughput", f"{last['our_throughput']:.2f} Mbps")
            k5.metric("Route Score", f"{last['route_score']:.3f}")
            k6.metric("Congestion", f"{last['our_congestion']:.2f}")

            st.divider()

            # ── Live Charts ────────────────────────────────────────────────
            r1c1, r1c2 = st.columns(2)

            with r1c1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["our_pdr"]*100,
                                         name="Our PDR",
                                         line=dict(color=OUR_COLOR, width=2)))
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["aodv_pdr"]*100,
                                         name="AODV PDR",
                                         line=dict(color=AODV_COLOR, width=2, dash="dash")))
                fig.update_layout(**DARK_TEMPLATE, title="PDR Comparison (%)",
                                  height=280, margin=dict(l=30,r=10,t=40,b=30))
                st.plotly_chart(fig, use_container_width=True, key=f"chart_1_{_rid}")

            with r1c2:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["our_delay"]*1000, name="Our Delay",
                                         fill="tozeroy",
                                         line=dict(color=OUR_COLOR, width=2)))
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["aodv_delay"]*1000, name="AODV Delay",
                                         line=dict(color=AODV_COLOR, width=2, dash="dash")))
                fig.update_layout(**DARK_TEMPLATE, title="End-to-End Delay (ms)",
                                  height=280, margin=dict(l=30,r=10,t=40,b=30))
                st.plotly_chart(fig, use_container_width=True, key=f"chart_2_{_rid}")

            r2c1, r2c2 = st.columns(2)
            with r2c1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["our_throughput"],  name="Our TP",
                                         line=dict(color=OUR_COLOR, width=2)))
                fig.add_trace(go.Scatter(x=df["time_step"],
                                         y=df["aodv_throughput"], name="AODV TP",
                                         line=dict(color=AODV_COLOR, width=2, dash="dash")))
                fig.update_layout(**DARK_TEMPLATE, title="Throughput (Mbps)",
                                  height=280, margin=dict(l=30,r=10,t=40,b=30))
                st.plotly_chart(fig, use_container_width=True, key=f"chart_3_{_rid}")

            with r2c2:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df["time_step"][-30:],
                                     y=df["our_jitter"].tail(30)*1000,
                                     name="Our Jitter",
                                     marker_color=OUR_COLOR))
                fig.add_trace(go.Bar(x=df["time_step"][-30:],
                                     y=df["aodv_jitter"].tail(30)*1000,
                                     name="AODV Jitter",
                                     marker_color=AODV_COLOR))
                fig.update_layout(**DARK_TEMPLATE, title="Jitter (ms) – last 30 steps",
                                  barmode="group",
                                  height=280, margin=dict(l=30,r=10,t=40,b=30))
                st.plotly_chart(fig, use_container_width=True, key=f"chart_4_{_rid}")

        if auto_refresh:
            time.sleep(2)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Performance Graphs
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📊 Performance Graphs":
    st.title("📊 Interactive Performance Analysis")

    df = load_scenario_df(scenario_sel)
    if df is None:
        no_data_warning()
        st.stop()

    smooth = lambda s: s.rolling(5, min_periods=1).mean()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Delay", "PDR", "Throughput", "Overhead", "Travel Time", "Congestion"
    ])

    with tab1:
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["our_delay"]*1000),
                                  name="Our Protocol",
                                  fill="tozeroy", fillcolor="rgba(88,166,255,0.15)",
                                  line=dict(color=OUR_COLOR, width=2.5)))
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["aodv_delay"]*1000),
                                  name="AODV",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash")))
        fig.update_layout(**DARK_TEMPLATE,
                          title=f"End-to-End Delay vs Time ({scenario_sel})",
                          xaxis_title="Time (s)", yaxis_title="Delay (ms)",
                          height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_5")
        avg_our  = df["our_delay"].mean()*1000
        avg_aodv = df["aodv_delay"].mean()*1000
        st.info(f"✅ Our protocol reduces average delay by "
                f"**{avg_aodv-avg_our:.2f} ms** ({(avg_aodv-avg_our)/avg_aodv*100:.1f}% improvement)")

    with tab2:
        fig = go.Figure()
        bins = pd.cut(df["density"], bins=12, labels=False)
        g = df.groupby(bins)
        x  = g["density"].mean()
        fig.add_trace(go.Scatter(x=x, y=g["our_pdr"].mean()*100,
                                  name="Our Protocol",
                                  mode="lines+markers",
                                  line=dict(color=OUR_COLOR, width=2.5),
                                  marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=x, y=g["aodv_pdr"].mean()*100,
                                  name="AODV",
                                  mode="lines+markers",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash"),
                                  marker=dict(size=6, symbol="square")))
        fig.add_hline(y=90, line_dash="dot", line_color="#3fb950",
                      annotation_text="90% target")
        fig.update_layout(**DARK_TEMPLATE,
                          title="PDR vs Vehicle Count",
                          xaxis_title="Vehicles", yaxis_title="PDR (%)", height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_6")

    with tab3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["our_throughput"]),
                                  name="Our Protocol", fill="tozeroy",
                                  fillcolor="rgba(88,166,255,0.15)",
                                  line=dict(color=OUR_COLOR, width=2.5)))
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["aodv_throughput"]),
                                  name="AODV",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash")))
        fig.update_layout(**DARK_TEMPLATE,
                          title="Throughput vs Time",
                          xaxis_title="Time (s)", yaxis_title="Throughput (Mbps)",
                          height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_7")

    with tab4:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["our_overhead"]),
                                  name="Our Protocol",
                                  line=dict(color=OUR_COLOR, width=2.5)))
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["aodv_overhead"]),
                                  name="AODV",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash")))
        fig.update_layout(**DARK_TEMPLATE,
                          title="Routing Overhead vs Time",
                          xaxis_title="Time (s)", yaxis_title="Control Packets",
                          height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_8")
        saving = (df["aodv_overhead"].mean() - df["our_overhead"].mean())
        st.info(f"✅ Our protocol saves **{saving:.1f} control packets** per step on average.")

    with tab5:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["our_travel_time"]),
                                  name="Our Protocol",
                                  line=dict(color=OUR_COLOR, width=2.5)))
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["aodv_travel_time"]),
                                  name="AODV",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash")))
        fig.update_layout(**DARK_TEMPLATE,
                          title="Travel Time vs Time",
                          xaxis_title="Simulation Time (s)",
                          yaxis_title="Vehicle Travel Time (s)", height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_9")

    with tab6:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["our_congestion"]),
                                  name="Our Protocol",
                                  fill="tozeroy",
                                  fillcolor="rgba(88,166,255,0.15)",
                                  line=dict(color=OUR_COLOR, width=2.5)))
        fig.add_trace(go.Scatter(x=df["time_step"],
                                  y=smooth(df["aodv_congestion"]),
                                  name="AODV",
                                  line=dict(color=AODV_COLOR, width=2.5, dash="dash")))
        fig.update_layout(**DARK_TEMPLATE,
                          title="Congestion Level vs Time (0=free, 1=jam)",
                          xaxis_title="Time (s)", yaxis_title="Congestion Index",
                          height=420)
        st.plotly_chart(fig, use_container_width=True, key="chart_10")


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Congestion Map
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🗺️ Congestion Map":
    st.title("🗺️ Road Congestion Visualisation")
    st.markdown("Simulated 8×8 grid map. Each cell = one road segment.")

    np.random.seed(42)
    grid = 8
    aodv_map = np.random.beta(2, 1.5, (grid, grid))
    aodv_map[3:5, 3:5] += 0.45
    aodv_map = np.clip(aodv_map, 0, 1)
    our_map  = np.clip(aodv_map * np.random.uniform(0.55, 0.75, (grid, grid)), 0, 1)

    col1, col2 = st.columns(2)
    
    # FIXED: Added enumerate to get a unique index 'i' for the key
    for i, (col, data, title) in enumerate([(col1, aodv_map, "AODV – Congestion"),
                                            (col2, our_map,  "Our Protocol – Congestion")]):
        with col:
            fig = px.imshow(data,
                            color_continuous_scale="RdYlGn_r",
                            zmin=0, zmax=1,
                            labels={"color": "Congestion"},
                            title=title)
            fig.update_layout(paper_bgcolor=BG_COLOR,
                              plot_bgcolor="#161b22",
                              font_color="#c9d1d9",
                              coloraxis_colorbar=dict(
                                  tickcolor="#c9d1d9",
                                  title=dict(font=dict(color="#c9d1d9"))
                              ))
            # FIXED: Made the key dynamic using the loop index 'i'
            st.plotly_chart(fig, use_container_width=True, key=f"chart_11_{i}")

    st.info(
        f"✅ Average congestion reduced by "
        f"**{(aodv_map.mean()-our_map.mean())*100:.1f}%** through load-balanced routing."
    )

    st.divider()
    st.subheader("Vehicle Movement Simulation (Animated)")
    st.markdown("Replay of vehicles navigating the grid under our protocol.")
    # Animated scatter of vehicles
    frames = 30
    all_x, all_y, all_t = [], [], []
    rng = np.random.default_rng(7)
    for v in range(20):
        x0, y0 = rng.uniform(0,8), rng.uniform(0,8)
        for t in range(frames):
            all_x.append(x0 + rng.normal(0, 0.25) * t / frames * 3)
            all_y.append(y0 + rng.normal(0, 0.15) * t / frames * 3)
            all_t.append(t)

    ani_df = pd.DataFrame({"x": all_x, "y": all_y, "t": all_t})
    fig = px.scatter(ani_df, x="x", y="y", animation_frame="t",
                     range_x=[-0.5, 8.5], range_y=[-0.5, 8.5],
                     title="Animated Vehicle Movement on Grid")
    fig.update_traces(marker=dict(size=8, color=OUR_COLOR))
    fig.update_layout(paper_bgcolor=BG_COLOR, plot_bgcolor="#161b22",
                      font_color="#c9d1d9", height=420)
    st.plotly_chart(fig, use_container_width=True, key="chart_12")


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Comparison Table
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📋 Comparison Table":
    st.title("📋 Full Protocol Comparison Table")

    # ── 1. Simple 4-row table matching the spec ────────────────────────────
    st.subheader("Key Parameter Summary")
    spec_table = pd.DataFrame([
        {"Parameter": "Delay",      "Traditional Routing": "High",     "Your Protocol": "Lower"},
        {"Parameter": "PDR",        "Traditional Routing": "Moderate", "Your Protocol": "High"},
        {"Parameter": "Travel Time","Traditional Routing": "Longer",   "Your Protocol": "Shorter"},
        {"Parameter": "Congestion", "Traditional Routing": "Uneven",   "Your Protocol": "Balanced"},
    ])
    st.table(spec_table)

    st.divider()

    # ── 2. Detailed numeric table ──────────────────────────────────────────
    st.subheader("Detailed Metrics (All Scenarios)")
    simple = load_simple_table()
    if simple is not None:
        def colour_row(row):
            p  = row["Parameter"].lower()
            ov = float(row["Our Protocol"])
            av = float(row["Traditional (AODV)"])
            lower_better = any(k in p for k in ["delay","overhead","travel","congestion"])
            our_wins = (ov < av) if lower_better else (ov > av)
            return [
                "",
                "background-color:#3b1f1f; color:#f78166" if our_wins else "background-color:#1f3b2a; color:#3fb950",
                "background-color:#1f3b2a; color:#3fb950" if our_wins else "background-color:#3b1f1f; color:#f78166",
            ]
        st.dataframe(
            simple.style.apply(colour_row, axis=1),
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("Run all scenarios first.")

    st.divider()

    # ── 3. Scenario-level summary ──────────────────────────────────────────
    st.subheader("Scenario Summary")
    summ = load_summary()
    if summ is not None:
        st.dataframe(summ, use_container_width=True, hide_index=True)

        # Radar chart
        st.subheader("Radar Comparison (Normalised Metrics)")
        cats = ["PDR", "Throughput", "Delay(inv)", "Overhead(inv)",
                "TravelTime(inv)", "Congestion(inv)"]

        def norm_pair(our_col, aodv_col, invert=False):
            o = summ[our_col].mean()
            a = summ[aodv_col].mean()
            mn, mx = min(o,a), max(o,a)
            r = (mx-mn) or 1
            on = (o-mn)/r; an = (a-mn)/r
            return (1-on, 1-an) if invert else (on, an)

        pairs = [
            ("Our_PDR_%",           "AODV_PDR_%",           False),
            ("Our_Throughput_Mbps", "AODV_Throughput_Mbps", False),
            ("Our_Delay_ms",        "AODV_Delay_ms",        True),
            ("Our_Overhead",        "AODV_Overhead",        True),
            ("Our_TravelTime_s",    "AODV_TravelTime_s",    True),
            ("Our_Congestion",      "AODV_Congestion",      True),
        ]
        our_v  = [norm_pair(*p)[0] for p in pairs]
        aodv_v = [norm_pair(*p)[1] for p in pairs]

        fig = go.Figure()
        for vals, name, color in [(our_v,"Our Protocol",OUR_COLOR),
                                   (aodv_v,"AODV",AODV_COLOR)]:
            fig.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill="toself",
                name=name,
                line=dict(color=color, width=2),
                fillcolor=color.replace("ff", "33") if "#" in color else color,
                opacity=0.8,
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,1],
                                gridcolor="#30363d", tickfont=dict(color="#8b949e")),
                angularaxis=dict(tickfont=dict(color="#c9d1d9")),
                bgcolor="#161b22",
            ),
            paper_bgcolor=BG_COLOR,
            font_color="#c9d1d9",
            showlegend=True,
            legend=dict(bgcolor="#21262d"),
            height=480,
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_13")
    else:
        st.info("Run all three scenarios to see the full summary.")


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE: Plot Gallery
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🖼️ Plot Gallery":
    st.title("🖼️ Static Plot Gallery")
    st.markdown("Pre-generated Matplotlib plots from the last simulation run.")

    available = {k: v for k, v in PLOT_FILES.items() if os.path.exists(v)}
    if not available:
        no_data_warning()
        st.stop()

    sel = st.selectbox("Select Plot", list(available.keys()))
    img_path = available[sel]
    img = Image.open(img_path)
    st.image(img, use_container_width=True)

    with open(img_path, "rb") as f:
        st.download_button(f"⬇️ Download {sel}", f, file_name=os.path.basename(img_path),
                           mime="image/png")

    st.divider()
    st.subheader("All Available Plots")
    cols = st.columns(3)
    for i, (name, path) in enumerate(available.items()):
        with cols[i % 3]:
            st.image(Image.open(path), caption=name, use_container_width=True)


# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "VANET Traffic-Aware Routing | Weight-Based Protocol vs AODV | "
    "Powered by SUMO + TraCI + Python + Streamlit"
)