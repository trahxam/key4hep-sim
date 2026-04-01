#!/bin/bash
# Test run WITHOUT InnerVXDExtend fix (baseline)
set -e
set -x

NEV=${NEV:-10}
SAMPLE=p8_ee_Zuds_ecm91
SEED=999001
CONFIG_DIR=/afs/cern.ch/user/h/hart/cld/key4hep-sim/cld/CLDConfig
WORKDIR=/tmp/$USER/test_baseline_$$
OUTDIR=/afs/cern.ch/user/h/hart/cld/key4hep-sim/cld

mkdir -p $WORKDIR

cleanup() {
    echo "Cleaning up $WORKDIR"
    rm -rf $WORKDIR
}
trap cleanup EXIT

cd $WORKDIR

# Copy config (use baseline reco file)
cp -R $CONFIG_DIR ./
cp $CONFIG_DIR/CLDConfig/CLDReconstruction_baseline.py CLDConfig/CLDConfig/CLDReconstruction.py
cp $CONFIG_DIR/CLDConfig/${SAMPLE}.cmd card.cmd
echo "Random:seed=${SEED}" >> card.cmd

# Prepare the gen-sim-reco script
cat > sim.sh << 'SIMEOF'
#!/bin/bash
set -e
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-02-01
SIMEOF

cat >> sim.sh << SIMEOF
ls CLDConfig/CLDConfig
k4run CLDConfig/CLDConfig/pythia.py -n $NEV --Dumper.Filename out.hepmc --Pythia8.PythiaInterface.pythiacard card.cmd
ddsim -I out.hepmc -N -1 -O out_SIM.root --compactFile \$K4GEO/FCCee/CLD/compact/CLD_o2_v05/CLD_o2_v05.xml --steeringFile CLDConfig/CLDConfig/cld_steer.py
cd CLDConfig/CLDConfig
k4run CLDReconstruction.py --inputFiles ../../out_SIM.root --outputBasename out_RECO --num-events -1
SIMEOF

export PYTHONPATH=$(pwd)/CLDConfig/CLDConfig:$PYTHONPATH
bash sim.sh

cp CLDConfig/CLDConfig/out_RECO_edm4hep.root $OUTDIR/reco_test_baseline.root
echo "=== BASELINE TEST COMPLETE ==="
