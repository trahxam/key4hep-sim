import uproot
import awkward
import numpy as np
import sys

fname = sys.argv[1] if len(sys.argv) > 1 else "/eos/user/h/hart/cld/p8_ee_Zuds_ecm91/root/reco_p8_ee_Zuds_ecm91_looseTrk_1.root"

fi = uproot.open(fname)
ev = fi["events"]

print(f"File: {fname}\n")

# Check sim-level VertexBarrelCollection hits
for coll in ["VertexBarrelCollection", "VertexEndcapCollection"]:
    try:
        x = awkward.flatten(ev[f"{coll}/{coll}.position.x"].array())
        y = awkward.flatten(ev[f"{coll}/{coll}.position.y"].array())
        z = awkward.flatten(ev[f"{coll}/{coll}.position.z"].array())
        r = np.sqrt(np.array(x)**2 + np.array(y)**2)

        print(f"=== {coll} ===")
        print(f"  Total sim hits: {len(r)}")
        print(f"  r range: {r.min():.2f} - {r.max():.2f} mm")
        print()

        # bin by layer
        bins = [0, 15, 20, 40, 60, 80, 200]
        labels = ["r<15 (layer1a)", "15-20 (layer1b)", "20-40 (layer2)", "40-60 (layer3)", "60-80", ">80"]
        counts, _ = np.histogram(r, bins=bins)
        print("  SimHit radial distribution:")
        for label, count in zip(labels, counts):
            pct = 100 * count / len(r) if len(r) > 0 else 0
            print(f"    {label:20s}: {count:5d}  ({pct:5.1f}%)")
        print()

        # also show per-event counts at innermost layer
        x_ev = ev[f"{coll}/{coll}.position.x"].array()
        y_ev = ev[f"{coll}/{coll}.position.y"].array()
        r_ev = np.sqrt(x_ev**2 + y_ev**2)
        nhits_layer1 = awkward.sum(r_ev < 20, axis=1)
        nhits_layer2 = awkward.sum((r_ev >= 20) & (r_ev < 45), axis=1)
        nhits_total = awkward.num(r_ev)

        print(f"  Per-event hit counts:")
        print(f"    {'event':>5s}  {'total':>6s}  {'layer1(<20)':>12s}  {'layer2(20-45)':>14s}")
        for i in range(len(nhits_total)):
            print(f"    {i:5d}  {int(nhits_total[i]):6d}  {int(nhits_layer1[i]):12d}  {int(nhits_layer2[i]):14d}")
        print()

    except Exception as e:
        print(f"=== {coll} === NOT FOUND: {e}\n")

# Now check digitized VXDTrackerHits
for coll in ["VXDTrackerHits", "VXDEndcapTrackerHits"]:
    try:
        x = awkward.flatten(ev[f"{coll}/{coll}.position.x"].array())
        y = awkward.flatten(ev[f"{coll}/{coll}.position.y"].array())
        r = np.sqrt(np.array(x)**2 + np.array(y)**2)

        print(f"=== {coll} (digitized) ===")
        print(f"  Total digi hits: {len(r)}")
        if len(r) > 0:
            print(f"  r range: {r.min():.2f} - {r.max():.2f} mm")
            bins = [0, 15, 20, 40, 60, 80, 200]
            labels = ["r<15 (layer1a)", "15-20 (layer1b)", "20-40 (layer2)", "40-60 (layer3)", "60-80", ">80"]
            counts, _ = np.histogram(r, bins=bins)
            print("  DigiHit radial distribution:")
            for label, count in zip(labels, counts):
                pct = 100 * count / len(r) if len(r) > 0 else 0
                print(f"    {label:20s}: {count:5d}  ({pct:5.1f}%)")
        print()
    except Exception as e:
        print(f"=== {coll} (digitized) === NOT FOUND: {e}\n")
