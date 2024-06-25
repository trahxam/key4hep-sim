import uproot
import glob

#for fi in glob.glob("/local/joosep/clic_edm4hep/2024_03/p8_ee_Z_Ztautau_ecm380/*.hepmc"):
for fi in glob.glob("/local/joosep/clic_edm4hep/2024_03/p8_ee_qq_ecm380/*.root"):
    try:
        tt = uproot.open(fi)["events"]
    except Exception as e:
        print(e, fi)
