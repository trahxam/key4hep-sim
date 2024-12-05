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

# set the directories
rm -rf CLDConfig_tmp
mkdir CLDConfig_tmp
dir_to_bind=$(realpath CLDConfig_tmp)
cd $dir_to_bind

# copy inpit files
cp ../CLDConfig/CLDConfig/${SAMPLE}.cmd card.cmd
cp ../CLDConfig/CLDConfig/pythia.py pythia.py
cp ../CLDConfig/CLDConfig/cld_steer.py cld_steer.py
cp ../CLDConfig/CLDConfig/CLDReconstruction.py CLDReconstruction.py
cp -r ../CLDConfig/CLDConfig/PandoraSettingsCLD .

# update the seed in the pythia card
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


# echo "
# #!/bin/bash
# set -e
# source /cvmfs/sw.hsf.org/key4hep/setup.sh
# env
# k4run pythia.py -n $NEV --Dumper.Filename out.hepmc --Pythia8.PythiaInterface.pythiacard card.cmd
# ddsim -I out.hepmc -N -1 -O out_SIM.root --compactFile /afs/cern.ch/user/f/fmokhtar/k4geo/FCCee/ILD_FCCee/compact/ILD_FCCee_v02/ILD_FCCee_v02.xml --steeringFile cld_steer.py
# k4run CLDReconstruction.py --inputFiles out_SIM.root --outputBasename out_RECO --num-events -1
# " > sim.sh

# cat sim.sh

# run the event generation and PF reco
singularity exec -B /cvmfs -B $dir_to_bind docker://ghcr.io/key4hep/key4hep-images/alma9:latest bash sim.sh

cp out_RECO_edm4hep.root ../reco_${SAMPLE}_${JOBID}.root
cp out.hepmc ../sim_${SAMPLE}_${JOBID}.hepmc