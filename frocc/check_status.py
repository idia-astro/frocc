#!/usr/bin/python3
import subprocess
import sys
import os
import re

from frocc.check_output import print_output
from frocc.lhelpers import get_config_in_dot_notation, get_statusList, SEPERATOR, SEPERATOR_HEAVY
from frocc.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from frocc.logger import *

def print_header():
    headline = " [ frocc --status ] "
    decorationsLength = int(len(SEPERATOR_HEAVY)/2. - len(headline)/2.)
    header = SEPERATOR_HEAVY[:decorationsLength] + headline + SEPERATOR_HEAVY
    header = header[:len(SEPERATOR_HEAVY)]
    print(header)

def prepend_status_prefix_symbol(statusString, major=False):
    prefix = ""
    if re.search(r"PENDING|RUNNING", statusString):
        prefix = "?"
    elif re.search(r"FAILED", statusString):
        prefix = "\u2718"
    elif re.search(r"COMPLETE", statusString):
        prefix = "\u2714"
    if major:
        prefix = "[" + prefix + "] "
    else:
        prefix = " " + prefix + "  "
    return prefix + statusString

def print_slurm_status(statusList, conf):
    psps = prepend_status_prefix_symbol
    for name in [entry.replace(".py","") for entry in conf.input.runScripts]:
        mainJobs = [s for s in statusList if name in s]
        if mainJobs:
            print(psps(mainJobs[0], major=True))
            importantJobList = [s for s in mainJobs if re.search(r"FAILED|RUNNING", s)]
            for importantJob in importantJobList:
                print(f"{psps('  '+importantJob)}")


def print_status():
    print_header()
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    #check if config in current directory and if frocc --start has been run
    if not ( os.path.exists(FILEPATH_CONFIG_TEMPLATE) and os.path.exists(FILEPATH_CONFIG_USER)):
        print(f"ERROR: Could not find `{FILEPATH_CONFIG_TEMPLATE}` and/or `{FILEPATH_CONFIG_USER}`")
        print(f"Is this the right working directory?")
        sys.exit()
    if not  conf.data.slurmIDList:
        print(f"ERROR: No started slurm jobs found.")
        print(f"Did you already run `frocc --start` in this directory?")
        sys.exit()
    statusList = get_statusList(conf)
    print(SEPERATOR)
    print_slurm_status(statusList, conf)
    print(SEPERATOR)
    print_output()


if __name__ == "__main__":
    print_status()
