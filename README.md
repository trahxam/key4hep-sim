# CLD Sample Generation

## Getting Started

Clone the repo with the config:

```
git clone --recurse-submodules https://github.com/trahxam/key4hep-sim.git
cd key4hep-sim/cld
```

Update the paths in `submit.templ.jdl` and `run_sim.sh`

Submit the jobs on Condor:

```
condor_submit submit.templ.jdl
```
By default this will submit 100 jobs, each of which will produce one file containing 1000 events each. These, along with the pythia card choice, can be changed in `submit.temp.jdl`.



