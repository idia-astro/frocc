#!/usr/bin/python3
import subprocess
import sys
import os

from mightee_pol.lhelpers import get_config_in_dot_notation, SEPERATOR, SEPERATOR_HEAVY
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from mightee_pol.logger import *

def print_header():
    headline = " [ meerkat-pol --status ] "
    decorationsLength = int(len(SEPERATOR_HEAVY)/2. - len(headline)/2.)
    header = SEPERATOR_HEAVY[:decorationsLength] + headline + SEPERATOR_HEAVY
    header = header[:len(SEPERATOR_HEAVY)]
    print(header)

def get_statusList(conf):
    '''
    '''
    slurmIDcsv = ",".join(list(map(str, conf.data.slurmIDList)))
    command = f"sacct --jobs={slurmIDcsv} --format=jobname,jobid,state -P --delimiter ' '"
    #info(f"Slurm command: {command}")
    print(f"Working directory: {conf.data.workingDirectory}")
    print(f"Slurm command: {command}")
    sacctResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
    sacctResultStd = sacctResult.stdout# .replace("\n", " ")
    #info(sacctResultStd)
    statusList = sacctResultStd.split("\n")
    # parse the slurm job ID from sbatchResult
    if sacctResult.stderr:
        error(sacctResult.stderr)
        sys.exit()
    else:
        return statusList

def print_slurm_status(statusList, conf):
    for name in [entry.replace(".py","") for entry in conf.input.runScripts]:
        mainJobs = [s for s in statusList if name in s]
        print(mainJobs[0])
        failedJobList = [s for s in mainJobs if "FAILED" in s]
        for failedJob in failedJobList:
            print("  "+failedJob)
        runningJobList = [s for s in mainJobs if "RUNNING" in s]
        for runningJob in runningJobList:
            print("  "+runningJob)


def print_status():
    print_header()
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    #check if config in current directory and if meerkat --start has been run
    if not ( os.path.exists(FILEPATH_CONFIG_TEMPLATE) and os.path.exists(FILEPATH_CONFIG_USER)):
        print(f"ERROR: Could not find `{FILEPATH_CONFIG_TEMPLATE}` and/or `{FILEPATH_CONFIG_USER}`")
        print(f"Is this the right working directory?")
        sys.exit()
    try:
        test = conf.data.slurmIDList
    except:
        print(f"ERROR: No started slurm jobs found.")
        print(f"Did you already run `meerkat-pol --start` in this directory?")
        sys.exit()
    statusList = get_statusList(conf)
    print(SEPERATOR)
    print_slurm_status(statusList, conf)
    print(SEPERATOR)


if __name__ == "__main__":
    print_status()
