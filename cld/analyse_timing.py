"""
Analyse per-event per-algorithm timing from CLD reconstruction.

Reads the TTree "timing" from the output ROOT file (merged by EventTimingWriter).
Each branch is an algorithm name with wall-clock time in ms per event.

Usage:
    python analyse_timing.py reco_test_timing.root [output.pdf]
"""
import sys

import numpy as np
import uproot

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Algorithms grouped by reconstruction stage
STAGE_MAP = {
    "Digitisation": [
        "VXDBarrelDigitiser", "VXDEndcapDigitiser",
        "InnerPlanarDigiProcessor", "InnerEndcapPlanarDigiProcessor",
        "OuterPlanarDigiProcessor", "OuterEndcapPlanarDigiProcessor",
    ],
    "Tracking": [
        "MyConformalTracking", "ClonesAndSplitTracksFinder", "Refit",
        "MyTruthTrackFinder",
    ],
    "Calo Digitisation": [
        "MyDDCaloDigi_10ns", "MyDDCaloDigi_400ns", "MyDDSimpleMuonDigi",
    ],
    "Particle Flow": [
        "MyDDMarlinPandora_10ns", "MyDDMarlinPandora_400ns",
    ],
    "PFO Selection": [
        "MyCLICPfoSelectorDefault", "MyCLICPfoSelectorLoose",
        "MyCLICPfoSelectorTight",
    ],
    "Vertexing & Jets": [
        "VertexFinder", "JetClusteringAndRefiner",
        "VertexFinderUnconstrained",
    ],
    "Monitoring": [
        "MyClicEfficiencyCalculator", "MyRecoMCTruthLinker",
        "MyTrackChecker",
    ],
}

# Flatten for quick lookup: algo_name -> stage
ALGO_TO_STAGE = {}
for stage, algos in STAGE_MAP.items():
    for a in algos:
        ALGO_TO_STAGE[a] = stage


def assign_stage(name):
    return ALGO_TO_STAGE.get(name, "Other")


def load_timings(rootfile):
    """Load timing TTree and return {algo_name: array_of_ms} dict."""
    f = uproot.open(rootfile)
    tree = f["timing"]
    branches = [k for k in tree.keys() if k != "event"]
    data = {}
    for b in branches:
        data[b] = tree[b].array(library="np")
    n_events = len(tree["event"].array(library="np"))
    return data, branches, n_events


def print_summary(data, algo_names, n_events):
    """Print a per-algorithm and per-stage timing summary."""
    print(f"\n{'='*70}")
    print(f"  CLD Reconstruction Timing Summary  ({n_events} events)")
    print(f"{'='*70}")

    # Per-algorithm table
    means = []
    stds = []
    names = []
    for name in algo_names:
        vals = data[name]
        vals = vals[vals >= 0]  # skip -1 (didn't run)
        if len(vals) == 0:
            continue
        names.append(name)
        means.append(np.mean(vals))
        stds.append(np.std(vals))

    means = np.array(means)
    stds = np.array(stds)
    total_mean = np.sum(means)

    print(f"\n{'Algorithm':<40s} {'Mean (ms)':>10s} {'Std (ms)':>10s} {'Frac':>7s}")
    print(f"{'-'*40} {'-'*10} {'-'*10} {'-'*7}")
    for n, m, s in sorted(zip(names, means, stds), key=lambda x: -x[1]):
        frac = m / total_mean * 100 if total_mean > 0 else 0
        print(f"{n:<40s} {m:10.1f} {s:10.1f} {frac:6.1f}%")
    print(f"{'-'*40} {'-'*10} {'-'*10} {'-'*7}")
    print(f"{'TOTAL':<40s} {total_mean:10.1f}")

    # Per-stage summary
    stage_times = {}
    for n, m in zip(names, means):
        stage = assign_stage(n)
        stage_times[stage] = stage_times.get(stage, 0.0) + m

    print(f"\n{'Stage':<25s} {'Mean (ms)':>10s} {'Frac':>7s}")
    print(f"{'-'*25} {'-'*10} {'-'*7}")
    for stage, t in sorted(stage_times.items(), key=lambda x: -x[1]):
        frac = t / total_mean * 100 if total_mean > 0 else 0
        print(f"{stage:<25s} {t:10.1f} {frac:6.1f}%")
    print(f"{'-'*25} {'-'*10} {'-'*7}")
    print(f"{'TOTAL':<25s} {total_mean:10.1f}")
    print()

    return names, means, stds, stage_times


def make_plots(data, algo_names, algo_means, algo_stds,
               stage_times, n_events, outname):
    """Create timing summary plots."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f"CLD Reconstruction Timing ({n_events} events)",
                 fontsize=14, fontweight="bold")

    # --- 1. Per-algorithm mean time (horizontal bar) ---
    ax = axes[0, 0]
    order = np.argsort(algo_means)
    y_pos = np.arange(len(order))
    ax.barh(y_pos, algo_means[order], xerr=algo_stds[order],
            color="#2196F3", alpha=0.8, ecolor="gray", capsize=2)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([algo_names[i] for i in order], fontsize=7)
    ax.set_xlabel("Wall time per event (ms)")
    ax.set_title("Per-Algorithm Mean Time")

    # --- 2. Pie chart by stage ---
    ax = axes[0, 1]
    stages = list(stage_times.keys())
    values = [stage_times[s] for s in stages]
    colors = plt.cm.Set3(np.linspace(0, 1, len(stages)))
    wedges, texts, autotexts = ax.pie(
        values, labels=stages, autopct="%1.1f%%", colors=colors,
        pctdistance=0.8, textprops={"fontsize": 8})
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title("Time Fraction by Stage")

    # --- 3. Per-event total time ---
    ax = axes[1, 0]
    event_totals = np.zeros(n_events)
    for name in algo_names:
        vals = data[name]
        mask = vals >= 0
        event_totals[mask] += vals[mask]
    ax.bar(range(n_events), event_totals / 1000.0, color="#4CAF50", alpha=0.8)
    ax.set_xlabel("Event number")
    ax.set_ylabel("Total reco time (s)")
    ax.set_title(f"Per-Event Total Time (mean={np.mean(event_totals)/1000:.1f}s)")
    ax.axhline(np.mean(event_totals) / 1000.0, color="red", ls="--", lw=1,
               label=f"mean = {np.mean(event_totals)/1000:.1f}s")
    ax.legend()

    # --- 4. Stacked per-event breakdown by stage ---
    ax = axes[1, 1]
    stage_order = sorted(stage_times.keys(), key=lambda s: -stage_times[s])
    stage_event_times = {s: np.zeros(n_events) for s in stage_order}
    other_times = np.zeros(n_events)

    for name in algo_names:
        stage = assign_stage(name)
        vals = data[name].copy()
        vals[vals < 0] = 0
        if stage in stage_event_times:
            stage_event_times[stage] += vals
        else:
            other_times += vals

    bottom = np.zeros(n_events)
    colors_stacked = plt.cm.Set3(np.linspace(0, 1, len(stage_order) + 1))
    for idx, stage in enumerate(stage_order):
        ax.bar(range(n_events), stage_event_times[stage] / 1000.0,
               bottom=bottom / 1000.0, label=stage,
               color=colors_stacked[idx], alpha=0.9)
        bottom += stage_event_times[stage]
    if np.any(other_times > 0):
        ax.bar(range(n_events), other_times / 1000.0,
               bottom=bottom / 1000.0, label="Other",
               color=colors_stacked[-1], alpha=0.9)
    ax.set_xlabel("Event number")
    ax.set_ylabel("Reco time (s)")
    ax.set_title("Per-Event Time by Stage")
    ax.legend(fontsize=7, loc="upper right")

    plt.tight_layout()
    plt.savefig(outname, dpi=150, bbox_inches="tight")
    print(f"Saved {outname}")

    # Also save PNG
    png_name = outname.replace(".pdf", ".png")
    if png_name != outname:
        plt.savefig(png_name, dpi=150, bbox_inches="tight")
        print(f"Saved {png_name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyse_timing.py <timing_root_file> [output.pdf]")
        sys.exit(1)

    rootfile = sys.argv[1]
    outname = sys.argv[2] if len(sys.argv) > 2 else "timing_summary.pdf"

    data, algo_names, n_events = load_timings(rootfile)
    names, means, stds, stage_times = print_summary(data, algo_names, n_events)
    make_plots(data, names, np.array(means), np.array(stds),
               stage_times, n_events, outname)
