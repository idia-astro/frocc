#!/usr/bin/python3
import subprocess
import sys
import os
import re

from mightee_pol.lhelpers import get_config_in_dot_notation, get_basename_from_path, get_statusList, SEPERATOR, SEPERATOR_HEAVY
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from mightee_pol.logger import *

def print_header():
    headline = " [ Checking output files ... ] "
    decorationsLength = int(len(SEPERATOR_HEAVY)/2. - len(headline)/2.)
    header = SEPERATOR_HEAVY[:decorationsLength] + headline + SEPERATOR_HEAVY
    header = header[:len(SEPERATOR_HEAVY)]
    print(header)


def check_is_still_running(conf):
    statusList = get_statusList(conf, noisy=False)
    #runningJobList = [s for s in statusList if ("lkjflkj" or "COM") in s]
    runningJobList = [s for s in statusList if re.search(r"PENDING|RUNNING", s) ]
    if runningJobList:
        return True
    else:
        return False

def get_missingVisList(conf):
    missingVisList = []
    for ii, inputMS in enumerate(conf.input.inputMS):
        for channelNumber in conf.data.predictedOutputChannels[ii]:
            outputMS = (
                conf.env.dirVis
                + get_basename_from_path(inputMS)
                + conf.env.markerChannel
                + str(channelNumber).zfill(3)
                + ".ms"
            )
            if not os.path.exists(outputMS):
                missingVisList.append(outputMS)
    return missingVisList

def check_split_output(conf):
    missingVisList = get_missingVisList(conf)
    if missingVisList:
        print("Split seems to have failed for the following output visibilities:")
        for missingVis in missingVisList:
            print(f" {missingVis}")
    else:
        print("[\u2714] Checking `split` output: All visibilities are complete.")


def get_missingImageList(conf, mode=None):
    missingImageList = []
    flatChannelList = [item for sublist in conf.data.predictedOutputChannels for item in sublist]
    channelSet = set(flatChannelList)
    for channelNumber in channelSet:
        outputMS = (
            conf.env.dirImages
            + conf.input.basename
            + conf.env.markerChannel
            + str(channelNumber).zfill(3)
        )
        if mode == "smoothed":
            outputMS += conf.env.extTcleanImageSmoothed
        else:
            outputMS += conf.env.extTcleanImage
        if not os.path.exists(outputMS):
            missingImageList.append(outputMS)
    return missingImageList

def check_tclean_output(conf):
    missingImageList = get_missingImageList(conf)
    if conf.input.smoothbeam:
        missingImageList += get_missingImageList(conf, mode="smoothed")
    if missingImageList:
        print("[\u2718] Tclean seems to have failed for the following output images:")
        for missingImage in missingImageList:
            print(f" \u2718    {missingImage}")
    else:
        print("[\u2714] Checking `tclean` output: All images are complete.")

def check_final_output_files(conf):
    '''
    TODO: implement a get_missing....List() like in the other functions
    '''
    foundOutputFileList = []
    missingOutputFileList = []
    outputExtList = conf.env.outputExtList
    if conf.input.smoothbeam:
        outputExtList += conf.env.outputExtSmoothedList
    # 
    for outputExt in outputExtList:
        if conf.env[outputExt].lower().endswith(".hdf5"):
            filePath = os.path.join(conf.input.dirHdf5Output, conf.input.basename + conf.env[outputExt])
        else:
            filePath = conf.input.basename + conf.env[outputExt]
        if os.path.exists(filePath):
            foundOutputFileList.append(filePath)
        else:
            missingOutputFileList.append(filePath)
    if not missingOutputFileList:
        print("[\u2714] All ouput files are found:")
    else:
        print("[\u2718] Some output files are missing:")

    for foundOutputFile in foundOutputFileList:
        print(f" \u2714    {foundOutputFile}")
    for missingOutputFile in missingOutputFileList:
        print(f" \u2718    {missingOutputFile}")


def print_output():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    if not check_is_still_running(conf):
        print_header()
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
        #check if config in current directory and if meerkat --start has been run
        if not ( os.path.exists(FILEPATH_CONFIG_TEMPLATE) and os.path.exists(FILEPATH_CONFIG_USER)):
            print(f"ERROR: Could not find `{FILEPATH_CONFIG_TEMPLATE}` and/or `{FILEPATH_CONFIG_USER}`")
            print(f"Is this the right working directory?")
            sys.exit()
        check_is_still_running(conf)
        check_split_output(conf)
        check_tclean_output(conf)
        check_final_output_files(conf)
        print(SEPERATOR)


if __name__ == "__main__":
    print_output()
