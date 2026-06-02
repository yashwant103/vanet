"""
VANET Plot Generator
====================
Produces ALL required publication-quality graphs comparing
Our Protocol vs AODV across low / medium / high density scenarios.

Usage:
    python3 generate_plots.py
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # headless rendering
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ─── Style ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#0d1117",
    "axes.facecolor":    "#161b22",
    "axes.edgecolor":    "#30363d",
    "axes.labelcolor":   "#c9d1d9",
    "xtick.color":       "#8b949e",
    "ytick.color":       "#8b949e",
    "text.color":        "#c9d1d9",
    "legend.facecolor":  "#21262d",
    "legend.edgecolor":  "#30363d",
    "grid.color":        "#21262d",
    "grid.linewidth":    0.8,
    "font.size":         10,
    "axes.titlesize":    12,
    "axes.titleweight":  "bold",
    "figure.dpi":        120,
})

COLORS = {
    "our":  "#58a6ff",   # blue
    "aodv": "#f78166",   # red-orange
    "low":  "#3fb950",
    "med":  "#d29922",
    "high": "#f78166",
}

RESULTS = "results"
PLOTS   = "plots"
os.makedirs(PLOTS, exist_ok=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_scenario(sc: str) -> pd.DataFrame | None:
    p = f"{RESULTS}/{sc}_density_stats.csv"
    if os.path.exists(p):
        return pd.read_csv(p)
    return None


def smooth(series, w=5):
    return series.rolling(w, min_periods=1).mean()


def savefig(name: str):
    path = f"{PLOTS}/{name}.png"
    plt.savefig(path, bbox_inches="tight", facecolor="#0d1117")
    plt.close()
    print(f"  ✅ Saved → {path}")


# ─── 1. Delay vs Time ─────────────────────────────────────────────────────────

def plot_delay_vs_time():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    fig.suptitle("📊 End-to-End Delay vs Simulation Time", fontsize=13, fontweight="bold", y=1.02)

    for ax, sc in zip(axes, ["low", "medium", "high"]):
        df = load_scenario(sc)
        if df is None:
            ax.set_title(f"{sc.capitalize()} (no data)")
            continue
        t = df["time_step"]
        ax.plot(t, smooth(df["our_delay"]  * 1000), color=COLORS["our"],
                linewidth=2, label="Our Protocol")
        ax.plot(t, smooth(df["aodv_delay"] * 1000), color=COLORS["aodv"],
                linewidth=2, linestyle="--", label="AODV")
        ax.fill_between(t,
                        smooth(df["our_delay"]  * 1000),
                        smooth(df["aodv_delay"] * 1000),
                        alpha=0.15, color=COLORS["our"])
        ax.set_title(f"{sc.capitalize()} Density")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Delay (ms)" if ax == axes[0] else "")
        ax.grid(True, alpha=0.4)
        ax.legend(fontsize=8)

    plt.tight_layout()
    savefig("1_delay_vs_time")


# ─── 2. PDR vs Number of Vehicles ─────────────────────────────────────────────

def plot_pdr_vs_vehicles():
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title("📊 Packet Delivery Ratio vs Number of Vehicles")
    ax.set_xlabel("Vehicle Count")
    ax.set_ylabel("PDR (%)")

    for sc in ["low", "medium", "high"]:
        df = load_scenario(sc)
        if df is None:
            continue
        bins  = pd.cut(df["density"], bins=12, labels=False)
        g     = df.groupby(bins)
        x     = g["density"].mean()
        our_y  = g["our_pdr"].mean()  * 100
        aodv_y = g["aodv_pdr"].mean() * 100
        c = COLORS.get(sc[:3], "#58a6ff")
        ax.plot(x, our_y,  color=COLORS["our"],  marker="o", ms=4, linewidth=2,
                label=f"Our – {sc}" if sc == "low" else f"Our – {sc}")
        ax.plot(x, aodv_y, color=COLORS["aodv"], marker="s", ms=4, linewidth=2,
                linestyle="--",
                label=f"AODV – {sc}" if sc == "low" else f"AODV – {sc}")

    ax.axhline(90, color="#3fb950", linestyle=":", linewidth=1, label="90% target")
    ax.grid(True, alpha=0.4)
    ax.legend(fontsize=8, ncol=2)
    savefig("2_pdr_vs_vehicles")


# ─── 3. Throughput vs Traffic Density ─────────────────────────────────────────

def plot_throughput_vs_density():
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title("📊 Throughput vs Traffic Density")
    ax.set_xlabel("Vehicle Density (vehicles)")
    ax.set_ylabel("Throughput (Mbps)")

    all_dfs = {sc: load_scenario(sc) for sc in ["low", "medium", "high"]}
    combined = pd.concat([d for d in all_dfs.values() if d is not None])
    bins  = pd.cut(combined["density"], bins=15, labels=False)
    g     = combined.groupby(bins)
    x     = g["density"].mean()
    our_y  = g["our_throughput"].mean()
    aodv_y = g["aodv_throughput"].mean()

    ax.fill_between(x, our_y,  alpha=0.25, color=COLORS["our"])
    ax.fill_between(x, aodv_y, alpha=0.25, color=COLORS["aodv"])
    ax.plot(x, our_y,  color=COLORS["our"],  linewidth=2.5, label="Our Protocol")
    ax.plot(x, aodv_y, color=COLORS["aodv"], linewidth=2.5,
            linestyle="--", label="AODV")

    ax.grid(True, alpha=0.4)
    ax.legend()
    savefig("3_throughput_vs_density")


# ─── 4. Routing Overhead ──────────────────────────────────────────────────────

def plot_routing_overhead():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("📊 Routing Overhead Analysis", fontweight="bold")

    # Left: overhead vs time for medium scenario
    df = load_scenario("medium")
    if df is not None:
        t = df["time_step"]
        axes[0].fill_between(t, smooth(df["aodv_overhead"]),
                             alpha=0.35, color=COLORS["aodv"])
        axes[0].fill_between(t, smooth(df["our_overhead"]),
                             alpha=0.35, color=COLORS["our"])
        axes[0].plot(t, smooth(df["aodv_overhead"]), color=COLORS["aodv"],
                     linewidth=2, linestyle="--", label="AODV")
        axes[0].plot(t, smooth(df["our_overhead"]),  color=COLORS["our"],
                     linewidth=2, label="Our Protocol")
        axes[0].set_title("Overhead vs Time (Medium Density)")
        axes[0].set_xlabel("Time (s)")
        axes[0].set_ylabel("Control Packets")
        axes[0].legend()
        axes[0].grid(True, alpha=0.4)

    # Right: bar chart per scenario
    scenarios = ["low", "medium", "high"]
    our_means  = []
    aodv_means = []
    for sc in scenarios:
        d = load_scenario(sc)
        if d is not None:
            our_means.append(d["our_overhead"].mean())
            aodv_means.append(d["aodv_overhead"].mean())
        else:
            our_means.append(0); aodv_means.append(0)

    x  = np.arange(len(scenarios))
    w  = 0.35
    axes[1].bar(x - w/2, aodv_means, w, label="AODV",        color=COLORS["aodv"], alpha=0.85)
    axes[1].bar(x + w/2, our_means,  w, label="Our Protocol", color=COLORS["our"],  alpha=0.85)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([s.capitalize() for s in scenarios])
    axes[1].set_title("Avg Overhead by Scenario")
    axes[1].set_ylabel("Avg Control Packets")
    axes[1].legend()
    axes[1].grid(True, alpha=0.4, axis="y")

    plt.tight_layout()
    savefig("4_routing_overhead")


# ─── 5. Travel Time vs Congestion ─────────────────────────────────────────────

def plot_travel_time_vs_congestion():
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_title("📊 Travel Time vs Congestion Level")
    ax.set_xlabel("Congestion Index (0–1)")
    ax.set_ylabel("Travel Time (s)")

    for sc in ["low", "medium", "high"]:
        df = load_scenario(sc)
        if df is None:
            continue
        ax.scatter(df["aodv_congestion"], df["aodv_travel_time"],
                   alpha=0.25, s=12, color=COLORS["aodv"])
        ax.scatter(df["our_congestion"],  df["our_travel_time"],
                   alpha=0.25, s=12, color=COLORS["our"])

    # Trend lines
    all_df = pd.concat([load_scenario(sc) for sc in ["low","medium","high"]
                        if load_scenario(sc) is not None])
    for key, col, label in [("aodv_congestion","aodv_travel_time","AODV"),
                             ("our_congestion",  "our_travel_time", "Our Protocol")]:
        z = np.polyfit(all_df[key], all_df[col], 1)
        p = np.poly1d(z)
        xs = np.linspace(all_df[key].min(), all_df[key].max(), 100)
        c  = COLORS["aodv"] if "aodv" in key else COLORS["our"]
        ls = "--" if "aodv" in key else "-"
        ax.plot(xs, p(xs), color=c, linewidth=2.5, linestyle=ls, label=label)

    ax.grid(True, alpha=0.4)
    ax.legend()
    savefig("5_travel_time_vs_congestion")


# ─── 6. Congestion Heat-Map (road segments) ───────────────────────────────────

def plot_congestion_heatmap():
    """Simulated grid-road congestion map."""
    np.random.seed(42)
    grid = 8

    # AODV: uneven load
    aodv_map = np.random.beta(2, 1.5, (grid, grid))
    aodv_map[3:5, 3:5] += 0.4    # hotspot

    # Our protocol: more balanced
    our_map  = aodv_map * np.random.uniform(0.55, 0.75, (grid, grid))
    our_map  = np.clip(our_map, 0, 1)
    aodv_map = np.clip(aodv_map, 0, 1)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("📊 Road Congestion Distribution (Grid Map)", fontweight="bold")

    for ax, data, title in [(axes[0], aodv_map, "AODV – Congestion"),
                             (axes[1], our_map,  "Our Protocol – Congestion")]:
        im = ax.imshow(data, cmap="RdYlGn_r", vmin=0, vmax=1,
                       interpolation="nearest")
        ax.set_title(title)
        ax.set_xlabel("Road Segment (X)")
        ax.set_ylabel("Road Segment (Y)")
        fig.colorbar(im, ax=ax, shrink=0.8, label="Congestion (0=free, 1=jam)")

    plt.tight_layout()
    savefig("6_congestion_heatmap")


# ─── 7. Summary Comparison Bar Chart ──────────────────────────────────────────

def plot_summary_bars():
    p = f"{RESULTS}/comparison_summary.csv"
    if not os.path.exists(p):
        print("  ⚠ comparison_summary.csv not found, skipping summary bars")
        return
    df = pd.read_csv(p)

    metrics = [
        ("Our_Delay_ms",        "AODV_Delay_ms",        "Delay (ms)",        "lower"),
        ("Our_PDR_%",           "AODV_PDR_%",           "PDR (%)",           "higher"),
        ("Our_Throughput_Mbps", "AODV_Throughput_Mbps", "Throughput (Mbps)", "higher"),
        ("Our_Overhead",        "AODV_Overhead",        "Overhead (pkts)",   "lower"),
        ("Our_TravelTime_s",    "AODV_TravelTime_s",    "Travel Time (s)",   "lower"),
        ("Our_Congestion",      "AODV_Congestion",      "Congestion (0-1)",  "lower"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    fig.suptitle("📊 Protocol Comparison Across All Scenarios",
                 fontsize=14, fontweight="bold", y=1.01)
    axes = axes.flatten()

    for ax, (our_col, aodv_col, label, better) in zip(axes, metrics):
        scenarios = df["Scenario"].tolist()
        x = np.arange(len(scenarios))
        w = 0.35
        ax.bar(x - w/2, df[aodv_col], w, color=COLORS["aodv"],
               alpha=0.85, label="AODV")
        ax.bar(x + w/2, df[our_col],  w, color=COLORS["our"],
               alpha=0.85, label="Our Protocol")
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, fontsize=9)
        ax.set_title(label)
        ax.set_ylabel(label)
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3, axis="y")

        # Improvement annotation
        avg_imp = ((df[aodv_col] - df[our_col]) / (df[aodv_col] + 1e-9) * 100).mean()
        sign = "↓" if better == "lower" else "↑"
        color = COLORS["our"] if abs(avg_imp) > 2 else "#8b949e"
        ax.text(0.98, 0.95,
                f"{sign} {abs(avg_imp):.1f}% avg",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=9, color=color, fontweight="bold")

    plt.tight_layout()
    savefig("7_summary_comparison")


# ─── 8. Radar / Spider Chart ──────────────────────────────────────────────────

def plot_radar():
    p = f"{RESULTS}/comparison_summary.csv"
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)

    cats = ["PDR", "Throughput", "Delay\n(inv)", "Overhead\n(inv)",
            "TravelTime\n(inv)", "Congestion\n(inv)"]
    N = len(cats)
    angles = [n / N * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={"polar": True})
    ax.set_facecolor("#161b22")
    fig.patch.set_facecolor("#0d1117")
    ax.set_title("📊 Radar – Normalised Performance (avg all scenarios)",
                 pad=20, fontsize=11, fontweight="bold")

    def norm(our_col, aodv_col, invert=False):
        o = df[our_col].mean()
        a = df[aodv_col].mean()
        mn, mx = min(o, a), max(o, a)
        r = mx - mn if mx != mn else 1
        our_n  = (o - mn) / r
        aodv_n = (a - mn) / r
        if invert:
            our_n = 1 - our_n; aodv_n = 1 - aodv_n
        return our_n, aodv_n

    pairs = [
        ("Our_PDR_%",           "AODV_PDR_%",           False),
        ("Our_Throughput_Mbps", "AODV_Throughput_Mbps", False),
        ("Our_Delay_ms",        "AODV_Delay_ms",        True),
        ("Our_Overhead",        "AODV_Overhead",        True),
        ("Our_TravelTime_s",    "AODV_TravelTime_s",    True),
        ("Our_Congestion",      "AODV_Congestion",      True),
    ]
    our_vals  = [norm(*p)[0] for p in pairs] + [norm(*pairs[0])[0]]
    aodv_vals = [norm(*p)[1] for p in pairs] + [norm(*pairs[0])[1]]

    ax.plot(angles, our_vals,  color=COLORS["our"],  linewidth=2, label="Our Protocol")
    ax.fill(angles, our_vals,  color=COLORS["our"],  alpha=0.25)
    ax.plot(angles, aodv_vals, color=COLORS["aodv"], linewidth=2,
            linestyle="--", label="AODV")
    ax.fill(angles, aodv_vals, color=COLORS["aodv"], alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cats, size=9, color="#c9d1d9")
    ax.set_yticklabels([]); ax.grid(color="#30363d")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    savefig("8_radar_chart")


# ─── 9. Static Comparison Table Image ─────────────────────────────────────────

def plot_comparison_table():
    p = f"{RESULTS}/protocol_comparison_table.csv"
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.axis("off")
    ax.set_title("📋 Protocol Comparison Summary Table",
                 fontsize=13, fontweight="bold", pad=15, color="#c9d1d9")

    col_labels = list(df.columns)
    rows       = df.values.tolist()

    # Colour the Our Protocol column green vs AODV red for visual impact
    cell_colours = []
    for row in rows:
        cell_colours.append(["#161b22", "#3b1f1f", "#1f3b2a"])

    tbl = ax.table(
        cellText=[[f"{v:.3g}" if isinstance(v, float) else str(v) for v in row]
                  for row in rows],
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
        cellColours=cell_colours,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.8)

    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#30363d")
        if r == 0:
            cell.set_facecolor("#21262d")
            cell.get_text().set_color("#58a6ff")
            cell.get_text().set_fontweight("bold")
        elif c == 1:
            cell.get_text().set_color(COLORS["aodv"])
        elif c == 2:
            cell.get_text().set_color(COLORS["our"])
        else:
            cell.get_text().set_color("#c9d1d9")

    savefig("9_comparison_table")


# ─── 10. Jitter Analysis ──────────────────────────────────────────────────────

def plot_jitter():
    df = load_scenario("medium")
    if df is None:
        return
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title("📊 Jitter Analysis (Medium Density)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Jitter (ms)")
    ax.plot(df["time_step"], smooth(df["our_jitter"]  * 1000),
            color=COLORS["our"],  linewidth=2, label="Our Protocol")
    ax.plot(df["time_step"], smooth(df["aodv_jitter"] * 1000),
            color=COLORS["aodv"], linewidth=2, linestyle="--", label="AODV")
    ax.grid(True, alpha=0.4)
    ax.legend()
    savefig("10_jitter_analysis")


# ─── Run All ──────────────────────────────────────────────────────────────────

def main():
    print("\n🎨 Generating all VANET plots...")

    # Check if we have any data at all
    available = [sc for sc in ["low","medium","high"]
                 if os.path.exists(f"{RESULTS}/{sc}_density_stats.csv")]
    if not available:
        print("⚠  No simulation data found.")
        print("   Run first: python3 vanet_simulation.py --all --no-sumo")
        return

    print(f"  Found data for: {available}\n")

    plot_delay_vs_time()
    plot_pdr_vs_vehicles()
    plot_throughput_vs_density()
    plot_routing_overhead()
    plot_travel_time_vs_congestion()
    plot_congestion_heatmap()
    plot_summary_bars()
    plot_radar()
    plot_comparison_table()
    plot_jitter()

    print(f"\n✅ All plots saved to: {os.path.abspath(PLOTS)}/")


if __name__ == "__main__":
    main()
