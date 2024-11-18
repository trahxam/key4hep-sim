#!/usr/bin/python

import argparse
import os


def main(args):

    if not os.path.exists(f"condor/{args.tag}"):
        os.makedirs(f"condor/{args.tag}")

    Nevents = args.Nevents
    Nevents_per_file = args.Nevents_per_file

    Njobs = Nevents // Nevents_per_file

    for jobid in range(Njobs):  # jobid marks the random seed

        # make condor submit file with the specified jobid and sample
        localcondor = f"condor/{args.tag}/{args.sample}_{jobid}.jdl"

        condor_templ_file = open("submit.templ.jdl")
        condor_file = open(localcondor, "w")
        for line in condor_templ_file:

            line = line.replace("NEV", str(Nevents_per_file))
            line = line.replace("SAMPLE", args.sample)
            line = line.replace("JOBID", str(jobid))
            line = line.replace("TAG", args.tag)

            condor_file.write(line)

        condor_file.close()
        condor_templ_file.close()

        # submit
        if args.submit:
            print("Submit ", localcondor)
            os.system("condor_submit %s" % localcondor)


if __name__ == "__main__":
    """
    python3 submit.py --sample p8_ee_tt_ecm365 --Nevents 4 --Nevents-per-file 2 --tag Nov15 --submit
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", default="", help="which sample to generate", type=str)
    parser.add_argument("--Nevents", default=4, help="how many events to generate", type=int)
    parser.add_argument("--Nevents-per-file", default=2, help="how many events to store per file", type=int)
    parser.add_argument("--submit", action="store_true", help="submit jobs when created")
    parser.add_argument("--tag", default="", help="dir tag", type=str)

    args = parser.parse_args()

    main(args)
