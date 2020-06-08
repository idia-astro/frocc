#/usr/bin/env python3
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
import configparser
from mightee_pol.logger import *

# own helpers
from mightee_pol.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, main_timer, write_sbtach_file, get_firstFreq, get_basename_from_path, get_optimal_taskNo_cpu_mem, SEPERATOR
from mightee_pol.config import SPECIAL_FLAGS
import mightee_pol

os.environ['LC_ALL'] = "C.UTF-8"
os.environ['LANG'] = "C.UTF-8"

# need to be instaled in container. Right now linkt with $PYTHONPATH
import click

# non defaults
import numpy as np


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS


FILEPATH_CONFIG_USER = "default_config.txt"
PATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_CONFIG_TEMPLATE = ".default_config.template"
FILEPATH_CONFIG_TEMPLATE_ORIGINAL = os.path.join(PATH_PACKAGE, FILEPATH_CONFIG_TEMPLATE)

# TODO: handle this better. Maybe a config.py? Right now this is a checken-egg-problem, therefore hardcoded
FILEPATH_LOG_PIPELINE = "pipeline.log"
FILEPATH_LOG_TIMER = "timer.log"

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# HELPER
#Hey so I just realized there's a much faster way to do the --createScripts step in your pipeline
#9:03
#Instead of using msmd try using the tb tool and opening the SPECTRAL_WINDOW subtable
#9:03
#You can access it by tb.open('msname::SPECTRAL_WINDOW')
#9:04
#and then tb.colnames() will tell you the list of columns in that table, and tb.getcol('chan_freqs') will give you a list of channel frequencies`meerkat --createScripts --copyScripts`

def get_all_freqsList(conf, msIdx):
    """
    Problem: Gets all frequencies in frequency range, not only the valid ones!
    Get all the frequencies of all the channels in each spw.
    """
    from casatools import table  # work around sice this script get executed in different environments/containers
    allFreqsList = np.array([])
    info(f"Opening file to read the frequency coverage of all channels in each spw: {conf.input.inputMS[msIdx]}")
    #mstb = tb.open(conf.input.inputMS[msIdx] + "::SPECTRAL_WINDOW")
    tb = table()
    tb.open(tablename=conf.input.inputMS[msIdx]+"/SPECTRAL_WINDOW")
    chanFreqArray = tb.getcol('CHAN_FREQ')
    chanWidthArray = tb.getcol('CHAN_WIDTH')
    allFreqsList = np.append(allFreqsList, (chanFreqArray + chanWidthArray))
    allFreqsList = np.append(allFreqsList, (chanFreqArray - chanWidthArray))
    return allFreqsList

def get_all_freqsList_old(conf, msIdx):
    """
    Get all the frequencies of all the channels in each spw.
    """
    from casatools import msmetadata  # work around sice this script get executed in different environments/containers
    allFreqsList = np.array([])
    info(f"Opening file to read the frequency coverage of all channels in each spw: {conf.input.inputMS[msIdx]}")
    msmd = msmetadata()
    msmd.open(msfile=conf.input.inputMS[msIdx], maxcache=10000)
    for spw in range(0, msmd.nspw()):
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) + msmd.chanwidths(spw)))
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) - msmd.chanwidths(spw)))
    return allFreqsList


def get_fields(conf, msIdx):
    """
    Get all the frequencies of all the channels in each spw.
    TODO: put all the msmd in one fuction so that the object is created only once.
    """
    from casatools import table  # work around sice this script get executed in different environments/containers
    info(f"Opening file to read the fields: {conf.input.inputMS[msIdx]}")
    tb = table()
    tb.open(tablename=conf.input.inputMS[msIdx]+"/FIELD")
    return list(tb.getcol('NAME'))

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
            # don't write these flags to the config file
            if key in [ item.replace("-", "") for item in SPECIAL_FLAGS]:
                continue
            if key == "inputMS":
                try:
                    isinstance(eval(value), list)
                except:
                    # convert string to list, split at, strip whitespace and all back to a string again to write it to config
                    value = str([x.strip() for x in list(filter(None, value.split(",")))])
                if "basename" not in args.keys():
                    configInputStringArray.append("basename" + " = " + get_basename_from_path(value, withTimestamp=True))
            configInputStringArray.append(key + " = " + value)

        # Read the config template file first to populate them into the Default
        # config file.
        config = configparser.ConfigParser(allow_no_value=True, strict=False, interpolation=configparser.ExtendedInterpolation())
        # In order to prevent key to get converted to lower case
        config.optionxform = lambda option: option
        config.read([FILEPATH_CONFIG_TEMPLATE_ORIGINAL])
        for key, value in config['input'].items():
            if key not in args.keys() and key != "basename":
                configInputStringArray.append(key + " = " + value)

        configString += "\n".join(configInputStringArray)
        f.write(configString)

def update_user_config_data(data):
    '''
    TODO: this needs to be replaced if existing, not appended
    '''
    info(f"Appending msdata to file: {data}, {FILEPATH_CONFIG_USER}")
    with open(FILEPATH_CONFIG_USER, "r") as f:
        fullConfigString = f.read()
    # Check whether [data] exists and either append or update
    if fullConfigString.find("\n[data]\n") < 0:
        configString = "\n\n[data]\n"
    else:
        configString = "\n"
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
        if not os.path.exists(conf.env[directory]):
            os.makedirs(conf.env[directory])


def write_all_sbatch_files(conf):
    '''
    TODO: make this shorter and better
    '''
    # split
    slurmArrayLength = str(sum([len(x) for x in conf.data.predictedOutputChannels]))
    # limit the split jobs to run in parallel, since they seem to cause I/O trouble.
    if 99 < int(slurmArrayLength):
        slurmArrayMaxTaks = 99
    else:
        slurmArrayMaxTaks = slurmArrayLength
    numberInputMS = len(conf.input.inputMS)
    slurmMemory = 20
    if slurmMemory > int(conf.env.tcleanMaxMemory):
        slurmMemory = int(conf.env.tcleanMaxMemory)
    basename = "cube_split"
    filename = basename + ".sbatch"
    sbatchDict = {
        'array': f"1-{slurmArrayLength}%{slurmArrayMaxTaks}",
        'job-name': basename,
        'cpus-per-task': 1,
        'mem': str(slurmMemory) + "GB",
        'output': f"logs/{basename}-%A-%a.out",
        'error': f"logs/{basename}-%A-%a.err",
        }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath + ' --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, conf, sbatchDict)

    # tclean
    slurmArrayLength = str(len(set(itertools.chain(*conf.data.predictedOutputChannels))))
    tcleanSlurm = get_optimal_taskNo_cpu_mem(conf)
    if int(tcleanSlurm['maxTasks']) > int(slurmArrayLength):
        tcleanSlurm['maxTasks'] = slurmArrayLength
    basename = "cube_tclean"
    filename = basename + ".sbatch"
    sbatchDict = {
        'array': f"1-{slurmArrayLength}%{tcleanSlurm['maxTasks']}",
        'job-name': basename,
        'cpus-per-task': tcleanSlurm['cpu'],
        'mem': str(tcleanSlurm['mem']) + "GB",
        'output': f"logs/{basename}-%A-%a.out",
        'error': f"logs/{basename}-%A-%a.err",
        }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath + ' --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, conf, sbatchDict)

    # buildcube
    if conf.input.smoothbeam:
        noOfArrayTasks = 2
    else:
        noOfArrayTasks = 1
    basename = "cube_buildcube"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': f"1-{noOfArrayTasks}%{noOfArrayTasks}",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 2,
            'mem': "50GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath + ' --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, conf, sbatchDict)

    # ior flagging
    basename = "cube_ior_flagging"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 8,
            'mem': str(tcleanSlurm['mem']) + "GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath
    write_sbtach_file(filename, command, conf, sbatchDict)

    # average map
    basename = "cube_average_map"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "100GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath
    write_sbtach_file(filename, command, conf, sbatchDict)

    # report
    basename = "cube_report"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "10GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath
    write_sbtach_file(filename, command, conf, sbatchDict)

    # generate rmsy input data
    basename = "cube_generate_rmsy_input_data"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "100GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath
    write_sbtach_file(filename, command, conf, sbatchDict)

    # do_rmsy
    basename = "cube_do_rmsy"
    filename = basename + ".sbatch"
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 1,
            'mem': "10GB",
            }
    if os.path.exists(basename + ".py"):
        scriptPath =  basename + ".py"
    else:
        scriptPath =  os.path.join(PATH_PACKAGE, basename + ".py")
    command = conf.env.prefixSingularity + ' python3 ' + scriptPath
    write_sbtach_file(filename, command, conf, sbatchDict)

def copy_runscripts(conf):
    '''
    Copies the runScripts to the local directory
    '''
    for script in conf.input.runScripts:
        shutil.copyfile(os.path.join(PATH_PACKAGE, script), script)

def get_field(fieldListList, conf):
    '''
    '''
    if conf.input.field:
        # check if field is in any fieldList
        flatList = [item for sublist in fieldListList for item in sublist]
        if conf.input.field in flatList:
            field = conf.input.field
        else:
            # TODO raise a proper error
            error(f"Field \'{conf.input.field}\' is not in {conf.input.inputMS}.")
            error(f"The following fields are found: {fieldListList}")
            sys.exit()
    elif len(fieldListList) > 1:
        for fieldList in fieldListList[1:]:
            fieldIntersection = set(fieldListList[0]).intersection(fieldList)
            if fieldIntersection:
                field = fieldIntersection.pop()
            else:
                warning(f"Measurement field missmatch please check input data: {fieldListList}")
                field = ""
                break
    else:
        field = fieldListList[0][0]
    info(f"Setting field to: {field}")
    return field

@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
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

        # iterate ofer multibple ms. This is necessary to feed tclean with multiple ms at once.
        data['workingDirectory'] = os.getcwd()
        data['predictedOutputChannels'] = []
        data['fields'] = []
        data['field'] = ""
        for msIdx, inputMS in enumerate(conf.input.inputMS):
            info(SEPERATOR)
            data['predictedOutputChannels'].append(get_unflagged_channelList(conf, msIdx))
            data['fields'].append(get_fields(conf, msIdx))
        data['field'] = get_field(data['fields'], conf)
        update_user_config_data(data)
        # reload conf after data got appended to user conf
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)

        #if conf.input.copyRunscripts:
        if "--copyScripts" in ctx.args:
            copy_runscripts(conf)

        write_all_sbatch_files(conf)

        return None  # ugly but maybe best solution, because of wrapper

    if "--start" in ctx.args:
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
        create_directories(conf)
        args = DotMap(get_dict_from_click_args(ctx.args))
        firstRunScript = conf.input.runScripts[0].replace('.py', '.sbatch')
        command = f"SLURMID=$(sbatch {firstRunScript} | cut -d ' ' -f4) && echo SLURMID: "
        for runScript in conf.input.runScripts[1:]:
            sbatchScript = runScript.replace(".py", ".sbatch")
            command += f"$SLURMID;SLURMID=$(sbatch --dependency=afterany:$SLURMID {sbatchScript} | cut -d ' ' -f4) && echo "
        command += "$SLURMID && echo Slurm jobs submitted!"
        info(f"Slurm command: {command}")
        sbatchResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        sbatchResultStd = sbatchResult.stdout.replace("\n", " ")
        info(sbatchResultStd)
        # parse the slurm job ID from sbatchResult
        slurmIDList = [ int(num) for num in sbatchResultStd.split() if num.isdigit() ]
        update_user_config_data({'slurmIDList': slurmIDList})
        if sbatchResult.stderr:
            error(sbatchResult.stderr)
        return None

    if "--cancel" in ctx.args or "--kill" in ctx.args:
        conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
        command = f'scancel {" ".join(map(str,conf.data.slurmIDList))}'
        info(f"Slurm command: {command}")
        sbatchResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
        sbatchResultStd = sbatchResult.stdout.replace("\n", " ")
        info(sbatchResultStd)
        if sbatchResult.stderr:
            error(sbatchResult.stderr)
        return None



if __name__ == '__main__':
    main()
