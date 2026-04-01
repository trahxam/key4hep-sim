#!/bin/bash
# Test run with per-event timing enabled (uses InnerVXDExtend fix)
set -e
set -x

NEV=${NEV:-10}
SAMPLE=${SAMPLE:-p8_ee_Zuds_ecm91}
SEED=999001
REPO_DIR=/afs/cern.ch/user/h/hart/cld/key4hep-sim/cld
CONFIG_DIR=${REPO_DIR}/CLDConfig
TIMING_DIR=${REPO_DIR}/EventTiming
WORKDIR=/tmp/$USER/test_timing_$$
OUTDIR=${REPO_DIR}

mkdir -p $WORKDIR

cleanup() {
    echo "Cleaning up $WORKDIR"
    rm -rf $WORKDIR
}
trap cleanup EXIT

cd $WORKDIR

# Copy config (use modified reco file with InnerVXDExtend)
cp -R $CONFIG_DIR ./
cp $CONFIG_DIR/CLDConfig/${SAMPLE}.cmd card.cmd
echo "Random:seed=${SEED}" >> card.cmd

# Build EventTiming plugin if needed
cat > sim.sh << 'SIMEOF'
#!/bin/bash
set -e
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-02-01
SIMEOF

cat >> sim.sh << SIMEOF
# Build the timing plugin
cd ${TIMING_DIR}
if [ ! -f build/libEventTimingPlugins.so ]; then
    mkdir -p build && cd build && cmake .. && make -j\$(nproc)
    cd ${TIMING_DIR}
fi
export LD_LIBRARY_PATH=${TIMING_DIR}/build:\$LD_LIBRARY_PATH
export PYTHONPATH=${TIMING_DIR}/build/genConfDir:\$PYTHONPATH

cd $WORKDIR

# 1. Event generation
k4run CLDConfig/CLDConfig/pythia.py -n $NEV --Dumper.Filename out.hepmc --Pythia8.PythiaInterface.pythiacard card.cmd

# 2. Detector simulation
# ddsim may SIGABRT at end-of-file cleanup (known issue); events are saved before that
ddsim -I out.hepmc -N -1 -O out_SIM.root --compactFile \$K4GEO/FCCee/CLD/compact/CLD_o2_v05/CLD_o2_v05.xml --steeringFile CLDConfig/CLDConfig/cld_steer.py || true
# verify sim output was actually produced
test -f out_SIM.root

# 3. Reconstruction with timing
cd CLDConfig/CLDConfig
k4run CLDReconstruction.py --inputFiles ../../out_SIM.root --outputBasename out_RECO --num-events -1 --enableTimings 2>&1 | tee ../../reco_timing.log
SIMEOF

export PYTHONPATH=$(pwd)/CLDConfig/CLDConfig:$PYTHONPATH
bash sim.sh

cp CLDConfig/CLDConfig/out_RECO_edm4hep.root $OUTDIR/reco_test_timing.root
cp reco_timing.log $OUTDIR/reco_timing.log
echo "=== TIMING TEST COMPLETE ==="
