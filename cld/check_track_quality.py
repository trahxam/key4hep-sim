import uproot
import awkward
import numpy as np
import sys

def analyze(fname):
    fi = uproot.open(fname)
    ev = fi["events"]

    # collection ID mapping
    meta = fi["podio_metadata"]
    coll_names = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.name"].array()[0]
    coll_ids = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.collectionID"].array()[0]
    id_to_name = {int(cid): str(name) for cid, name in zip(coll_ids, coll_names)}

    # track chi2/ndf
    chi2 = awkward.flatten(ev["SiTracks_Refitted/SiTracks_Refitted.chi2"].array())
    ndf = awkward.flatten(ev["SiTracks_Refitted/SiTracks_Refitted.ndf"].array())
    chi2 = np.array(chi2, dtype=float)
    ndf = np.array(ndf, dtype=float)
    ndf[ndf == 0] = 1  # avoid division by zero
    chi2ndf = chi2 / ndf

    # number of hits per track
    hits_begin = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_begin"].array()
    hits_end = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_end"].array()
    nhits = awkward.flatten(hits_end - hits_begin)
    nhits = np.array(nhits)

    # truth link weights (purity)
    try:
        link_weights = awkward.flatten(ev["SiTracksMCTruthLink/SiTracksMCTruthLink.weight"].array())
        link_weights = np.array(link_weights)
        has_truth = True
    except Exception:
        has_truth = False

    # MC charged particles (status=1, charged, pT > 0.1 GeV)
    mc_px = ev["MCParticles/MCParticles.momentum.x"].array()
    mc_py = ev["MCParticles/MCParticles.momentum.y"].array()
    mc_pz = ev["MCParticles/MCParticles.momentum.z"].array()
    mc_charge = ev["MCParticles/MCParticles.charge"].array()
    mc_status = ev["MCParticles/MCParticles.generatorStatus"].array()

    mc_pt = np.sqrt(mc_px**2 + mc_py**2)
    mc_charged_st1 = awkward.sum((mc_status == 1) & (np.abs(mc_charge) > 0.5) & (mc_pt > 0.1), axis=1)
    total_mc_charged = int(awkward.sum(mc_charged_st1))

    n_tracks = len(chi2ndf)
    n_events = len(hits_begin)

    print(f"  Events: {n_events}")
    print(f"  MC charged (status=1, pT>0.1): {total_mc_charged}")
    print(f"  Reco tracks: {n_tracks}")
    print(f"  Tracks/event: {n_tracks/n_events:.1f}")
    print()
    print(f"  chi2/ndf:  mean={np.mean(chi2ndf):.2f}  median={np.median(chi2ndf):.2f}  90th={np.percentile(chi2ndf, 90):.2f}  99th={np.percentile(chi2ndf, 99):.2f}")
    print(f"  nHits:     mean={np.mean(nhits):.1f}  median={np.median(nhits):.1f}  min={np.min(nhits)}  max={np.max(nhits)}")
    print()

    if has_truth:
        # truth link: one entry per track-MC association
        # the weight represents the fraction of hits from that MC particle
        # for best match per track, we need to group by track
        link_from_idx = ev["_SiTracksMCTruthLink_from/_SiTracksMCTruthLink_from.index"].array()
        link_from_cid = ev["_SiTracksMCTruthLink_from/_SiTracksMCTruthLink_from.collectionID"].array()
        link_to_idx = ev["_SiTracksMCTruthLink_to/_SiTracksMCTruthLink_to.index"].array()
        link_wt = ev["SiTracksMCTruthLink/SiTracksMCTruthLink.weight"].array()

        # reco D0 from first track state
        trk_ts_begin = ev["SiTracks_Refitted/SiTracks_Refitted.trackStates_begin"].array()
        reco_d0_all = ev["_SiTracks_Refitted_trackStates/_SiTracks_Refitted_trackStates.D0"].array()

        # MC vertex positions and momenta for true d0 calculation
        mc_vx = ev["MCParticles/MCParticles.vertex.x"].array()
        mc_vy = ev["MCParticles/MCParticles.vertex.y"].array()

        # for each event, find the best (highest weight) match per track
        n_fake = 0
        n_low_purity = 0
        best_weights = []
        d0_residuals = []
        for iev in range(n_events):
            # group links by track index, store best weight and MC index
            trk_best = {}
            for ilink in range(len(link_wt[iev])):
                trk_idx = int(link_from_idx[iev][ilink])
                w = float(link_wt[iev][ilink])
                mc_idx = int(link_to_idx[iev][ilink])
                if trk_idx not in trk_best or w > trk_best[trk_idx][0]:
                    trk_best[trk_idx] = (w, mc_idx)

            n_tracks_ev = len(hits_begin[iev])
            for itrk in range(n_tracks_ev):
                if itrk in trk_best:
                    w, mc_idx = trk_best[itrk]
                    best_weights.append(w)
                    if w < 0.5:
                        n_low_purity += 1

                    # d0 residual: reco D0 vs MC truth d0
                    # The signed transverse impact parameter d0 is defined as
                    # the distance of closest approach of the track to the
                    # reference point (origin) in the transverse plane, with sign
                    # given by: d0 = -(vx * py - vy * px) / pT
                    # where (vx, vy) is the production vertex and (px, py) the
                    # momentum at production.
                    ts_idx = int(trk_ts_begin[iev][itrk])
                    reco_d0 = float(reco_d0_all[iev][ts_idx])

                    vx = float(mc_vx[iev][mc_idx])
                    vy = float(mc_vy[iev][mc_idx])
                    px = float(mc_px[iev][mc_idx])
                    py = float(mc_py[iev][mc_idx])
                    pt = np.sqrt(px**2 + py**2)
                    if pt > 0:
                        mc_d0_truth = -(vx * py - vy * px) / pt
                    else:
                        mc_d0_truth = 0.0

                    d0_residuals.append(reco_d0 - mc_d0_truth)
                else:
                    n_fake += 1
                    best_weights.append(0.0)

        best_weights = np.array(best_weights)
        d0_residuals = np.array(d0_residuals)
        print(f"  Truth link purity (best match weight per track):")
        print(f"    mean={np.mean(best_weights):.3f}  median={np.median(best_weights):.3f}")
        print(f"    Tracks with no MC match (fake): {n_fake} ({100*n_fake/n_tracks:.1f}%)")
        print(f"    Tracks with purity < 0.5:       {n_low_purity} ({100*n_low_purity/n_tracks:.1f}%)")
        print(f"    Tracks with purity >= 0.75:     {np.sum(best_weights >= 0.75)} ({100*np.sum(best_weights >= 0.75)/n_tracks:.1f}%)")
        print()

        # d0 resolution (only for well-matched tracks)
        good = best_weights >= 0.75
        # d0_residuals only has entries for matched tracks (not fakes)
        d0_good = d0_residuals[good[best_weights > 0]]
        if len(d0_good) > 0:
            print(f"  D0 resolution (matched tracks, purity>=0.75, N={len(d0_good)}):")
            print(f"    mean residual:   {np.mean(d0_good)*1000:.1f} um")
            print(f"    std (RMS):       {np.std(d0_good)*1000:.1f} um")
            print(f"    median |resid|:  {np.median(np.abs(d0_good))*1000:.1f} um")
            print(f"    90th |resid|:    {np.percentile(np.abs(d0_good), 90)*1000:.1f} um")
    print()


files = sys.argv[1:] if len(sys.argv) > 1 else [
    "/eos/user/h/hart/cld/p8_ee_Zuds_ecm91/root/reco_p8_ee_Zuds_ecm91_1.root",
    "/eos/user/h/hart/cld/p8_ee_Zuds_ecm91/root/reco_p8_ee_Zuds_ecm91_looseTrk_1.root",
]

for fname in files:
    print(f"=== {fname.split('/')[-1]} ===")
    analyze(fname)
