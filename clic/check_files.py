import os

#check for file presence in this path
outpath = "/local/joosep/clic_edm4hep/2024_07"

#pythia card, start seed, end seed
samples = [
    ("p8_ee_tt_ecm380",              1,  80011),
    ("p8_ee_qq_ecm380",         100001, 180011),
    ("p8_ee_ZH_Htautau_ecm380", 200001, 240011),
    ("p8_ee_Z_Ztautau_ecm380",  400001, 440011),
    ("p8_ee_WW_fullhad_ecm380", 300001, 380011),
]

if __name__ == "__main__":
    for sname, seed0, seed1 in samples:
        os.makedirs(os.path.join(outpath, sname, "root"), exist_ok=True)
        os.makedirs(os.path.join(outpath, sname, "sim"), exist_ok=True)
        for seed in range(seed0, seed1):
            #check if output file exists, and print out batch submission if it doesn't
            if not os.path.isfile("{}/{}/root/reco_{}_{}.root".format(outpath, sname, sname, seed)):
                print("sbatch run_sim.sh {} {}".format(seed, sname)) 
