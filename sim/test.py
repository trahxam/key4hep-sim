import pyhepmc
import glob

#for fi in glob.glob("/local/joosep/clic_edm4hep/2024_03/p8_ee_Z_Ztautau_ecm380/*.hepmc"):
for fi in glob.glob("/local/joosep/clic_edm4hep/2024_03/p8_ee_ZH_Htautau_ecm380/*.hepmc"):
    with pyhepmc.open(fi) as f:
        events = []
        for event in f:
            events.append(event)
        print(fi, len(events))
