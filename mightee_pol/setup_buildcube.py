#!python3
# -*- coding: utf-8 -*-
import sys
import logging
import datetime
import itertools
import os
import time
import shutil
import re
import subprocess
from logging import info, error, warning

# own helpers
from mightee_pol.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, main_timer, write_sbtach_file, get_firstFreq, get_basename_from_path, get_optimal_taskNo_cpu_mem, SEPERATOR
import mightee_pol

os.environ['LC_ALL'] = "C.UTF-8"
os.environ['LANG'] = "C.UTF-8"

# need to be instaled in container. Right now linkt with $PYTHONPATH
import click

# non defaults
import numpy as np


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)

FILEPATH_CONFIG_USER = "default_config.txt"
PATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_CONFIG_TEMPLATE = ".default_config.template"
FILEPATH_CONFIG_TEMPLATE_ORIGINAL = os.path.join(PATH_PACKAGE, FILEPATH_CONFIG_TEMPLATE)

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# HELPER
def get_all_freqsList(conf, msIdx):
    """
    Get all the frequencies of all the channels in each spw.
    """
    from casatools import msmetadata  # work around sice this script get executed in different environments/containers
    allFreqsList = np.array([])
    info(f"Opening file to read the frequencies of all channels in each spw: {conf.input.inputMS[msIdx]}")
    msmd = msmetadata()
    msmd.open(msfile=conf.input.inputMS[msIdx], maxcache=10000)
    for spw in range(0, msmd.nspw()):
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) + msmd.chanwidths(spw)))
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) - msmd.chanwidths(spw)))
    return allFreqsList


def get_fieldnames(conf, msIdx):
    """
    Get all the frequencies of all the channels in each spw.
    TODO: put all the msmd in one fuction so that the object is created only once.
    """
    from casatools import msmetadata  # work around sice this script get executed in different environments/containers
    info(f"Opening file to read the fieldnames: {conf.input.inputMS[msIdx]}")
    msmd = msmetadata()
    msmd.open(msfile=conf.input.inputMS[msIdx], maxcache=10000)
    return msmd.fieldnames()

def get_unflagged_channelIndexBoolList(conf, msIdx):
    '''
    '''
    def get_subrange_unflagged_channelIndexSet(firstFreq, startFreq, stopFreq):
        allFreqsList = np.array(get_all_freqsList(conf, msIdx))
        rangeFreqsList = allFreqsList[(allFreqsList >= startFreq) & (allFreqsList <= stopFreq)]
        # A list of indexes for all cube channels in range that will hold data.
        # Expl: ( 901e6 [Hz] - 890e6 [Hz] ) // 2.5e6 [Hz] = 4 [listIndex]
        channelIndexList = [
            int((freq - firstFreq) // conf.input.outputChanBandwidth) for freq in rangeFreqsList
        ]
        channelIndexSet = set(channelIndexList)
        return channelIndexSet

    rangedChannelIndexSet = set()
    firstFreq = get_firstFreq(conf)
    for freqRange in conf.input.freqRanges:
        # TODO: ask if this can be done shorter
        startFreq, stopFreq = freqRange.split("-")
        startFreq = float(startFreq) * 1e6
        stopFreq = float(stopFreq) * 1e6
        rangedChannelIndexSet = rangedChannelIndexSet.union(get_subrange_unflagged_channelIndexSet(firstFreq, startFreq, stopFreq))

    maxChannelIndex = max(rangedChannelIndexSet)
    # True if cube channel holds data, otherwise False
    channelIndexBoolList = []
    for ii in range(0, maxChannelIndex + 1):
        if ii in rangedChannelIndexSet:
            channelIndexBoolList.append(True)
        else:
            channelIndexBoolList.append(False)
    return channelIndexBoolList

def get_unflagged_channelList(conf, msIdx):
    channelList = []
    channelIndexBoolList = get_unflagged_channelIndexBoolList(conf, msIdx)
    for i, channelBool in enumerate(channelIndexBoolList):
        if channelBool:
            channelList.append(i+1)
    return channelList

# HELPER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def write_user_config_input(args):
    '''
    '''
    info(f"Writing user input to config file: {FILEPATH_CONFIG_USER}")
    configString = "# This is the configuration file to initialise the mightee_pol cube generation.\n"
    configString += "# Please change the parameters accordingly.\n\n"
    configString += f"# Default values are read from the template file {FILEPATH_CONFIG_TEMPLATE}.\n"
    configString += "# Parameters from the template file can be used in this file you are editing\n"
    configString += "# here to overwrite the defaults.\n"
    configString += "#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n\n"
    configString += "[input]\n"
    configInputStringArray = []
    with open(FILEPATH_CONFIG_USER, 'w') as f:
        for key, value in args.items():
            if key in ["createConfig", "createScripts", "start"]:
                continue
            if key == "inputMS":
                try:
                    isinstance(eval(value), list)
                except:
                    # convert string to list, split at, strip whitespace and all back to a string again to write it to config
                    value = str([x.strip() for x in list(filter(None, value.split(",")))])
                configInputStringArray.append("basename" + " = " + get_basename_from_path(value))
            configInputStringArray.append(key + " = " + value)
            # don't write these flags to the config file
        configString += "\n".join(configInputStringArray)
        f.write(configString)

def append_user_config_data(data):
    '''
    TODO: this needs to be replaced if existing, not appended
    '''
    info(f"Appending msdata to file: {data}, {FILEPATH_CONFIG_USER}")
    configString = "\n\n[data]\n"
    configInputStringArray = []
    with open(FILEPATH_CONFIG_USER, 'a') as f:
        for key, value in data.items():
            configInputStringArray.append(key + " = " + str(value))
        configString += "\n".join(configInputStringArray)
        f.write(configString)


def create_directories(conf):
    """
    """
    for directory in list(conf.env.dirList):
        if not os.path.exists(directory):
            os.makedirs(directory)


def write_all_sbatch_files(conf):
    '''
    TODO: make this shorter and better
    '''
    # split
    slurmArrayLength = str(sum([len(x) for x in conf.data.predictedOutputChannels]))
    # limit the split jobs to run in parallel, since they seem to cause I/O trouble.
    if 100 < int(slurmArrayLength):
        slurmArrayMaxTaks = 100
    else:
        slurmArrayMaxTaks = slurmArrayLength
    basename = "cube_split"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
        'array': f"1-{slurmArrayLength}%{slurmArrayMaxTaks}",
        'job-name': basename,
        'cpus-per-task': 1,
        'mem': "10GB",
        'output': f"logs/{basename}-%A-%a.out",
        'error': f"logs/{basename}-%A-%a.err",
        }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, sbatchDict)

    # tclean
    slurmArrayLength = str(len(set(itertools.chain(*conf.data.predictedOutputChannels))))
    tcleanSlurm = get_optimal_taskNo_cpu_mem(conf)
    if int(tcleanSlurm['maxTasks']) > int(slurmArrayLength):
        tcleanSlurm['maxTasks'] = slurmArrayLength
    basename = "cube_tclean"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
        'array': f"1-{slurmArrayLength}%{tcleanSlurm['maxTasks']}",
        'job-name': basename,
        'cpus-per-task': tcleanSlurm['cpu'],
        'mem': tcleanSlurm['mem'],
        'output': f"logs/{basename}-%A-%a.out",
        'error': f"logs/{basename}-%A-%a.err",
        }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, sbatchDict)

    # buildcube
    if conf.input.smoothbeam:
        noOfArrayTasks = 2
    else:
        noOfArrayTasks = 1
    basename = "cube_buildcube"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': f"1-{noOfArrayTasks}%{noOfArrayTasks}",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 2,
            'mem': "50GB",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, sbatchDict)

    # ior flagging
    basename = "cube_ior_flagging"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "100GB",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py'
    write_sbtach_file(filename, command, sbatchDict)

    # generate rmsy input data
    basename = "cube_generate_rmsy_input_data"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "100GB",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py'
    write_sbtach_file(filename, command, sbatchDict)

    # do_rmsy
    basename = "cube_do_rmsy"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "10GB",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py'
    write_sbtach_file(filename, command, sbatchDict)

def copy_runscripts(conf):
    '''
    Copies the runScripts to the local directory
    '''
    for script in conf.env.runScripts:
        shutil.copyfile(os.path.join(PATH_PACKAGE, script), script)

def get_chosenField(fieldListList):
    '''
    '''
    if len(fieldListList) > 1:
        for fieldList in fieldListList[1:]:
            fieldIntersection = set(fieldListList[0]).intersection(fieldList)
            if fieldIntersection:
                chosenField = fieldIntersection.pop()
            else:
                warning(f"Measurement field missmatch please check input data: {fieldListList}")
                chosenField = "0"
                break
    else:
        chosenField = fieldListList[0][0]
    info(f"Setting chosenField to: {chosenField}")
    return chosenField

@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx):
    '''
    CAUTION: This method must be seen in combination with setup_buildcube_wrapper.py
    TODO: I made click super generic which is nice for development but we may
    want to change this for production.
    '''
    if "--createConfig" in ctx.args:
        # If not deleted this key would appear in the config file.
        # get the click args in dot dotation
        print(ctx.args)
        conf = DotMap(get_dict_from_click_args(ctx.args))
        info(f"Scripts arguments: {conf}")
        write_user_config_input(conf)
        # copy config template into local directory
        try:
            shutil.copy2(os.path.join(PATH_PACKAGE, FILEPATH_CONFIG_TEMPLATE_ORIGINAL), FILEPATH_CONFIG_TEMPLATE)
        except shutil.SameFileError:
            # TODO: check if this really works when packed in a python package
            pass
        return None  # ugly but maybe best solution, because of wrapper

    if "--createScripts" in ctx.args:
        # data: values derived from the measurement set like valid channels
        data = {}
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
        print(conf)

        # iterate ofer multibple ms. This is necessary to feed tclean with multiple ms at once.
        data['predictedOutputChannels'] = []
        data['fieldnames'] = []
        data['chosenField'] = ""
        for msIdx, inputMS in enumerate(conf.input.inputMS):
            info(SEPERATOR)
            data['predictedOutputChannels'].append(get_unflagged_channelList(conf, msIdx))
            data['fieldnames'].append(get_fieldnames(conf, msIdx))
        data['chosenField'] = get_chosenField(data['fieldnames'])
        append_user_config_data(data)
        # reload conf after data got appended to user conf
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)

        create_directories(conf)

        write_all_sbatch_files(conf)

        copy_runscripts(conf)
        return None  # ugly but maybe best solution, because of wrapper

    if "--start" in ctx.args:
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
        args = DotMap(get_dict_from_click_args(ctx.args))
        firstRunScript = conf.env.runScripts[0].replace('.py', '.sbatch')
        command = f"SLURMID=$(sbatch {firstRunScript} | cut -d ' ' -f4) && "
        for runScript in conf.env.runScripts[1:]:
            sbatchScript = runScript.replace(".py", ".sbatch")
            command += f"echo SLURMID: $SLURMID;SLURMID=$(sbatch --dependency=afterany:$SLURMID {sbatchScript} | cut -d ' ' -f4) && "
        command += "Slurm jobs submitted!"
        subprocess.run(command, shell=True)
        return None




if __name__ == '__main__':
    main()
