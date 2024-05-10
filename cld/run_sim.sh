#!/bin/bash
#SBATCH -p main
#SBATCH --mem-per-cpu=6G
#SBATCH --cpus-per-task=1
#SBATCH -o logs/slurm-%x-%j-%N.out
set -e
set -x

env
df -h

NEV=100
NUM=$1 #random seed
SAMPLE=$2 #main card

#Change these as needed
OUTDIR=/local/joosep/cld_edm4hep/2024_05/
SIMDIR=/home/joosep/key4hep-sim/cld/CLDConfig/CLDConfig
WORKDIR=/scratch/local/$USER/${SAMPLE}_${SLURM_JOB_ID}
FULLOUTDIR=${OUTDIR}/${SAMPLE}

mkdir -p $FULLOUTDIR

mkdir -p $WORKDIR
cd $WORKDIR

cp $SIMDIR/${SAMPLE}.cmd card.cmd
cp $SIMDIR/pythia.py ./
cp $SIMDIR/cld_steer.py ./
cp -R $SIMDIR/PandoraSettingsCLD ./
cp -R $SIMDIR/CLDReconstruction.py ./

echo "Random:seed=${NUM}" >> card.cmd
cat card.cmd

source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh

k4run pythia.py -n $NEV --Dumper.Filename out.hepmc --Pythia8.PythiaInterface.pythiacard card.cmd
ddsim -I out.hepmc -N -1 -O out_SIM.root --compactFile $K4GEO/FCCee/CLD/compact/CLD_o2_v05/CLD_o2_v05.xml --steeringFile cld_steer.py
k4run CLDReconstruction.py --inputFiles out_SIM.root --outputBasename out_RECO --num-events -1

#Copy the outputs
cp out_RECO_edm4hep.root $FULLOUTDIR/reco_${SAMPLE}_${NUM}.root
cp out.hepmc $FULLOUTDIR/sim_${SAMPLE}_${NUM}.hepmc

rm -Rf $WORKDIR
