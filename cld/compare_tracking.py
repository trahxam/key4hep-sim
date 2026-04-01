"""
Compare tracking performance between baseline and fixed (InnerVXDExtend) configurations.
Produces a multi-panel figure showing d0 resolution, innermost hit radius,
hit multiplicity, and doublet layer pickup.

Usage:
    python compare_tracking.py baseline.root fixed.root [output.pdf]
"""
import uproot
import awkward
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys


def load_track_data(fname):
    fi = uproot.open(fname)
    ev = fi["events"]
    meta = fi["podio_metadata"]

    coll_names = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.name"].array()[0]
    coll_ids = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.collectionID"].array()[0]
    id_to_name = {int(cid): str(name) for cid, name in zip(coll_ids, coll_names)}

    # basic track quantities
    chi2 = np.asarray(awkward.flatten(ev["SiTracks_Refitted/SiTracks_Refitted.chi2"].array()), dtype=float)
    ndf = np.asarray(awkward.flatten(ev["SiTracks_Refitted/SiTracks_Refitted.ndf"].array()), dtype=float)
    ndf[ndf == 0] = 1
    chi2ndf = chi2 / ndf

    hits_begin = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_begin"].array()
    hits_end = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_end"].array()
    nhits = np.asarray(awkward.flatten(hits_end - hits_begin))

    # hit collections for radius computation
    hit_collections = {}
    for coll in ["VXDTrackerHits", "VXDEndcapTrackerHits", "ITrackerHits",
                 "ITrackerEndcapHits", "OTrackerHits", "OTrackerEndcapHits"]:
        try:
            x = ev[f"{coll}/{coll}.position.x"].array()
            y = ev[f"{coll}/{coll}.position.y"].array()
            hit_collections[coll] = {"x": x, "y": y}
        except Exception:
            pass

    hit_refs_idx = ev["_SiTracks_Refitted_trackerHits/_SiTracks_Refitted_trackerHits.index"].array()
    hit_refs_cid = ev["_SiTracks_Refitted_trackerHits/_SiTracks_Refitted_trackerHits.collectionID"].array()

    # truth links
    link_from_idx = ev["_SiTracksMCTruthLink_from/_SiTracksMCTruthLink_from.index"].array()
    link_to_idx = ev["_SiTracksMCTruthLink_to/_SiTracksMCTruthLink_to.index"].array()
    link_wt = ev["SiTracksMCTruthLink/SiTracksMCTruthLink.weight"].array()

    # track states for reco d0
    trk_ts_begin = ev["SiTracks_Refitted/SiTracks_Refitted.trackStates_begin"].array()
    reco_d0_all = ev["_SiTracks_Refitted_trackStates/_SiTracks_Refitted_trackStates.D0"].array()

    # MC quantities
    mc_px = ev["MCParticles/MCParticles.momentum.x"].array()
    mc_py = ev["MCParticles/MCParticles.momentum.y"].array()
    mc_vx = ev["MCParticles/MCParticles.vertex.x"].array()
    mc_vy = ev["MCParticles/MCParticles.vertex.y"].array()

    n_events = len(hits_begin)

    # per-track loop
    innermost_r = []
    n_layer1_hits = []  # how many layer-1 doublet hits per track
    d0_residuals = []
    best_weights = []

    for iev in range(n_events):
        # build truth link map for this event
        trk_best = {}
        for ilink in range(len(link_wt[iev])):
            trk_idx = int(link_from_idx[iev][ilink])
            w = float(link_wt[iev][ilink])
            mc_idx = int(link_to_idx[iev][ilink])
            if trk_idx not in trk_best or w > trk_best[trk_idx][0]:
                trk_best[trk_idx] = (w, mc_idx)

        n_tracks = len(hits_begin[iev])
        for itrk in range(n_tracks):
            hbegin = int(hits_begin[iev][itrk])
            hend = int(hits_end[iev][itrk])

            min_r = 9999.0
            n_l1 = 0
            for ih in range(hbegin, hend):
                cid = int(hit_refs_cid[iev][ih])
                idx = int(hit_refs_idx[iev][ih])
                coll_name = id_to_name.get(cid, "")
                if coll_name in hit_collections:
                    hx = float(hit_collections[coll_name]["x"][iev][idx])
                    hy = float(hit_collections[coll_name]["y"][iev][idx])
                    r = np.sqrt(hx**2 + hy**2)
                    if r < min_r:
                        min_r = r
                    if r < 16:
                        n_l1 += 1

            innermost_r.append(min_r if min_r < 9999 else np.nan)
            n_layer1_hits.append(n_l1)

            # truth matching and d0
            if itrk in trk_best:
                w, mc_idx = trk_best[itrk]
                best_weights.append(w)
                ts_idx = int(trk_ts_begin[iev][itrk])
                reco_d0 = float(reco_d0_all[iev][ts_idx])
                vx = float(mc_vx[iev][mc_idx])
                vy = float(mc_vy[iev][mc_idx])
                px = float(mc_px[iev][mc_idx])
                py = float(mc_py[iev][mc_idx])
                pt = np.sqrt(px**2 + py**2)
                mc_d0 = -(vx * py - vy * px) / pt if pt > 0 else 0.0
                d0_residuals.append(reco_d0 - mc_d0)
            else:
                best_weights.append(0.0)
                d0_residuals.append(np.nan)

    return {
        "chi2ndf": chi2ndf,
        "nhits": nhits,
        "innermost_r": np.array(innermost_r),
        "n_layer1_hits": np.array(n_layer1_hits),
        "d0_residuals": np.array(d0_residuals),
        "best_weights": np.array(best_weights),
        "n_events": n_events,
    }


def make_plots(baseline, fixed, outname):
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle("Tracking Performance: Baseline vs InnerVXDExtend Fix", fontsize=14, fontweight="bold")

    colors = {"baseline": "#2196F3", "fixed": "#F44336"}
    labels = {"baseline": "Baseline", "fixed": "+ InnerVXDExtend"}

    # --- 1. Innermost hit radius ---
    ax = axes[0, 0]
    bins = np.arange(10, 80, 1)
    mask_b = ~np.isnan(baseline["innermost_r"]) & (baseline["innermost_r"] < 80)
    mask_f = ~np.isnan(fixed["innermost_r"]) & (fixed["innermost_r"] < 80)
    ax.hist(baseline["innermost_r"][mask_b], bins=bins, alpha=0.6, color=colors["baseline"],
            label=labels["baseline"], density=True)
    ax.hist(fixed["innermost_r"][mask_f], bins=bins, alpha=0.6, color=colors["fixed"],
            label=labels["fixed"], density=True)
    ax.set_xlabel("Radius of innermost hit [mm]")
    ax.set_ylabel("Fraction of tracks / mm")
    ax.set_title("Innermost Hit Radius")
    ax.legend()
    # mark doublet layers
    for r in [13.5, 14.5, 35.5, 36.5, 57.5, 58.5]:
        ax.axvline(r, color="gray", ls=":", lw=0.7)

    # --- 2. Layer-1 doublet hits per track ---
    ax = axes[0, 1]
    cats = [0, 1, 2]
    b_counts = [np.sum(baseline["n_layer1_hits"] == c) for c in cats]
    f_counts = [np.sum(fixed["n_layer1_hits"] == c) for c in cats]
    b_frac = np.array(b_counts) / len(baseline["n_layer1_hits"]) * 100
    f_frac = np.array(f_counts) / len(fixed["n_layer1_hits"]) * 100
    x = np.arange(len(cats))
    w = 0.35
    bars_b = ax.bar(x - w/2, b_frac, w, color=colors["baseline"], label=labels["baseline"])
    bars_f = ax.bar(x + w/2, f_frac, w, color=colors["fixed"], label=labels["fixed"])
    for bars in [bars_b, bars_f]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.0f}%", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(["0 hits", "1 hit", "2 hits"])
    ax.set_ylabel("% of tracks")
    ax.set_title("Layer-1 Doublet Hits per Track")
    ax.legend()

    # --- 3. nHits per track ---
    ax = axes[0, 2]
    bins = np.arange(2.5, 18.5, 1)
    ax.hist(baseline["nhits"], bins=bins, alpha=0.6, color=colors["baseline"],
            label=f'{labels["baseline"]} (mean={np.mean(baseline["nhits"]):.1f})', density=True)
    ax.hist(fixed["nhits"], bins=bins, alpha=0.6, color=colors["fixed"],
            label=f'{labels["fixed"]} (mean={np.mean(fixed["nhits"]):.1f})', density=True)
    ax.set_xlabel("Hits per track")
    ax.set_ylabel("Fraction of tracks")
    ax.set_title("Track Hit Multiplicity")
    ax.legend()

    # --- 4. d0 residual (all matched tracks) ---
    ax = axes[1, 0]
    good_b = baseline["best_weights"] >= 0.75
    d0_b = baseline["d0_residuals"][good_b & ~np.isnan(baseline["d0_residuals"])] * 1000  # um
    good_f = fixed["best_weights"] >= 0.75
    d0_f = fixed["d0_residuals"][good_f & ~np.isnan(fixed["d0_residuals"])] * 1000
    bins = np.linspace(-200, 200, 80)
    ax.hist(d0_b, bins=bins, alpha=0.6, color=colors["baseline"],
            label=f'{labels["baseline"]} (med |d0|={np.median(np.abs(d0_b)):.1f} um)', density=True)
    ax.hist(d0_f, bins=bins, alpha=0.6, color=colors["fixed"],
            label=f'{labels["fixed"]} (med |d0|={np.median(np.abs(d0_f)):.1f} um)', density=True)
    ax.set_xlabel("d0 residual (reco - truth) [um]")
    ax.set_ylabel("Fraction of tracks / bin")
    ax.set_title("d0 Resolution (purity >= 0.75)")
    ax.legend()

    # --- 5. |d0 residual| cumulative ---
    ax = axes[1, 1]
    sorted_b = np.sort(np.abs(d0_b))
    sorted_f = np.sort(np.abs(d0_f))
    ax.plot(sorted_b, np.arange(1, len(sorted_b)+1) / len(sorted_b),
            color=colors["baseline"], label=labels["baseline"], lw=2)
    ax.plot(sorted_f, np.arange(1, len(sorted_f)+1) / len(sorted_f),
            color=colors["fixed"], label=labels["fixed"], lw=2)
    ax.set_xlabel("|d0 residual| [um]")
    ax.set_ylabel("Cumulative fraction of tracks")
    ax.set_title("|d0| Residual CDF")
    ax.set_xlim(0, 300)
    ax.axhline(0.5, color="gray", ls="--", lw=0.7)
    ax.axhline(0.9, color="gray", ls="--", lw=0.7)
    ax.legend()

    # --- 6. chi2/ndf ---
    ax = axes[1, 2]
    bins = np.linspace(0, 15, 60)
    ax.hist(baseline["chi2ndf"], bins=bins, alpha=0.6, color=colors["baseline"],
            label=f'{labels["baseline"]} (med={np.median(baseline["chi2ndf"]):.2f})', density=True)
    ax.hist(fixed["chi2ndf"], bins=bins, alpha=0.6, color=colors["fixed"],
            label=f'{labels["fixed"]} (med={np.median(fixed["chi2ndf"]):.2f})', density=True)
    ax.set_xlabel("chi2 / ndf")
    ax.set_ylabel("Fraction of tracks / bin")
    ax.set_title("Track chi2/ndf")
    ax.legend()

    plt.tight_layout()
    plt.savefig(outname, dpi=150, bbox_inches="tight")
    print(f"Saved {outname}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_tracking.py baseline.root fixed.root [output.pdf]")
        sys.exit(1)

    fname_baseline = sys.argv[1]
    fname_fixed = sys.argv[2]
    outname = sys.argv[3] if len(sys.argv) > 3 else "tracking_comparison.pdf"

    print(f"Loading baseline: {fname_baseline}")
    baseline = load_track_data(fname_baseline)
    print(f"Loading fixed: {fname_fixed}")
    fixed = load_track_data(fname_fixed)

    make_plots(baseline, fixed, outname)
