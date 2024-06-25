import os

#check for file presence in this path
outpath = "/local/joosep/cld_edm4hep/2024_05/"

#pythia card, start seed, end seed
samples = [
    ("p8_ee_tt_ecm365",         100001, 100111),
]

if __name__ == "__main__":
    for sname, seed0, seed1 in samples:
        for seed in range(seed0, seed1):
            #check if output file exists, and print out batch submission if it doesn't
            if not os.path.isfile("{}/{}/reco_{}_{}.root".format(outpath, sname, sname, seed)):
                print("sbatch run_sim.sh {} {}".format(seed, sname)) 
