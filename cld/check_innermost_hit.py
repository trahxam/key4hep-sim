import uproot
import awkward
import numpy as np
import sys

fname = sys.argv[1] if len(sys.argv) > 1 else "/eos/user/h/hart/cld/p8_ee_Zuds_ecm91/root/reco_p8_ee_Zuds_ecm91_looseTrk_1.root"

fi = uproot.open(fname)
ev = fi["events"]

# get collection ID mapping
meta = fi["podio_metadata"]
coll_names = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.name"].array()[0]
coll_ids = meta["events___CollectionTypeInfo/events___CollectionTypeInfo.collectionID"].array()[0]
id_to_name = {int(cid): str(name) for cid, name in zip(coll_ids, coll_names)}

# load all tracker hit positions (VXD, inner tracker, outer tracker)
hit_collections = {}
for coll in ["VXDTrackerHits", "VXDEndcapTrackerHits", "ITrackerHits", "ITrackerEndcapHits", "OTrackerHits", "OTrackerEndcapHits"]:
    try:
        x = ev[f"{coll}/{coll}.position.x"].array()
        y = ev[f"{coll}/{coll}.position.y"].array()
        z = ev[f"{coll}/{coll}.position.z"].array()
        hit_collections[coll] = {"x": x, "y": y, "z": z}
    except Exception:
        pass

# load track -> hit references
trk_hits_begin = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_begin"].array()
trk_hits_end = ev["SiTracks_Refitted/SiTracks_Refitted.trackerHits_end"].array()
hit_refs_idx = ev["_SiTracks_Refitted_trackerHits/_SiTracks_Refitted_trackerHits.index"].array()
hit_refs_cid = ev["_SiTracks_Refitted_trackerHits/_SiTracks_Refitted_trackerHits.collectionID"].array()

# for each track, find the radius of the innermost hit
all_innermost_r = []
all_nhits_layer1 = 0
all_nhits_total = 0

for iev in range(len(trk_hits_begin)):
    n_tracks = len(trk_hits_begin[iev])
    for itrk in range(n_tracks):
        hbegin = trk_hits_begin[iev][itrk]
        hend = trk_hits_end[iev][itrk]

        min_r = 9999.0
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

        all_nhits_total += 1
        if min_r < 9999:
            all_innermost_r.append(min_r)

rih = np.array(all_innermost_r)

print(f"File: {fname}")
print(f"Total tracks: {len(rih)}")
print(f"radiusOfInnermostHit stats:")
print(f"  min:    {rih.min():.2f} mm")
print(f"  max:    {rih.max():.2f} mm")
print(f"  mean:   {rih.mean():.2f} mm")
print(f"  median: {np.median(rih):.2f} mm")
print()

# count tracks by which layer the innermost hit is on
# VXD barrel layers at ~13, 35, 57 mm
bins = [0, 20, 45, 70, 150, 500, 5000]
labels = ["<20 (layer1)", "20-45 (layer2)", "45-70 (layer3)", "70-150 (inner trk)", "150-500 (outer trk)", ">500"]
counts, _ = np.histogram(rih, bins=bins)
print("Innermost hit layer distribution:")
for label, count in zip(labels, counts):
    pct = 100 * count / len(rih) if len(rih) > 0 else 0
    print(f"  {label:25s}: {count:5d}  ({pct:5.1f}%)")
