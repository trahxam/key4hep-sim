#!/bin/bash
#SBATCH -p main
#SBATCH --mem-per-cpu=6G
#SBATCH --cpus-per-task=1
#SBATCH -o logs/slurm-%x-%j-%N.out
set -e
set -x

env
df -h

export NEV=$1  # number of events to generate per rootfile
export SAMPLE=$2 # main card
export JOBID=$3 # random seed

# alias for quick access of work directory
export USERDIR=/afs/cern.ch/user/f/fmokhtar
export WORKDIR=/afs/cern.ch/work/f/fmokhtar
export EOSDIR=/eos/user/f/fmokhtar/jobs_dir

mkdir -p $EOSDIR

# in your $USERDIR:
# git clone the key4hep-sim GitHub repo: https://github.com/HEP-KBFI/key4hep-sim/tree/main
# make sure to clone the CLDConfig repo https://github.com/jpata/CLDConfig/tree/982a1601e111feca4ccf4c4fcc6571d9a8f19d87 and put it in: key4hep-sim/cld/CLDConfig/CLDConfig and checkout 982a160

# set the directories (change these as needed)
export SIMDIR=${USERDIR}/key4hep-sim/cld/CLDConfig/CLDConfig
export JOBDIR=${WORKDIR}/jobs_dir/$USER/${SAMPLE}_${JOBID}

mkdir -p $JOBDIR
cd $JOBDIR

cp $SIMDIR/${SAMPLE}.cmd card.cmd
cp $SIMDIR/pythia.py ./
cp $SIMDIR/cld_steer.py ./
cp -R $SIMDIR/PandoraSettingsCLD ./
cp -R $SIMDIR/CLDReconstruction.py ./

echo "Random:seed=${JOBID}" >> card.cmd
cat card.cmd

echo "
#!/bin/bash
set -e
source /cvmfs/sw.hsf.org/key4hep/setup.sh
env
k4run pythia.py -n $NEV --Dumper.Filename out.hepmc --Pythia8.PythiaInterface.pythiacard card.cmd
ddsim -I out.hepmc -N -1 -O out_SIM.root --compactFile \$K4GEO/FCCee/CLD/compact/CLD_o2_v05/CLD_o2_v05.xml --steeringFile cld_steer.py
k4run CLDReconstruction.py --inputFiles out_SIM.root --outputBasename out_RECO --num-events -1
" > sim.sh

cat sim.sh

singularity exec -B /cvmfs -B $JOBDIR docker://ghcr.io/key4hep/key4hep-images/alma9:latest bash sim.sh
# singularity exec -B /cvmfs -B /scratch -B /local /home/software/singularity/alma9.simg bash sim.sh

#Copy the outputs to EOS
bzip2 out.hepmc
xrdcp out.hepmc.bz2 $EOSDIR/sim_${SAMPLE}_${JOBID}.hepmc.bz2
xrdcp out_RECO_edm4hep.root $EOSDIR/reco_${SAMPLE}_${JOBID}.root

cd ..
rm -Rf $JOBDIR

