import sys
import logging
import datetime
import os
import shutil
from logging import info, error

# own helpers
from mightee_pol.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, main_timer, write_sbtach_file, get_firstFreq
import mightee_pol

# need to be instaled in container. Right now linkt with $PYTHONPATH
import click

# non defaults
import numpy as np
from casatools import msmetadata


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

FILEPATH_CONFIG_USER = "default_config.txt"
FILEPATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_CONFIG_TEMPLATE = os.path.join(FILEPATH_PACKAGE, "default_config.template")

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# HELPER
def get_all_freqsList(conf):
    """
    Get all the frequencies of all the channels in each spw.
    """
    allFreqsList = np.array([])
    info("""Opening file to read the frequencies of all channels in each spw: {0}""".format(conf.input.inputMS))
    msmd = msmetadata()
    msmd.open(msfile=conf.input.inputMS, maxcache=10000)
    for spw in range(0, msmd.nspw()):
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) + msmd.chanwidths(spw)))
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) - msmd.chanwidths(spw)))
    return allFreqsList


def get_fieldnames(conf):
    """
    Get all the frequencies of all the channels in each spw.
    TODO: put all the msmd in one fuction so that the object is created only once.
    """
    info(f"Opening file to read the fieldnames: {conf.input.inputMS}")
    msmd = msmetadata()
    msmd.open(msfile=conf.input.inputMS, maxcache=10000)
    return msmd.fieldnames()

def get_unflagged_channelIndexBoolList(conf):
    '''
    '''
    def get_subrange_unflagged_channelIndexSet(firstFreq, startFreq, stopFreq):
        allFreqsList = np.array(get_all_freqsList(conf))
        # trim to range. TODO: How to do this in one line? Krishna?
        rangeFreqsList = allFreqsList[(allFreqsList >= startFreq) & (rangeFreqsList <= stopFreq)]
        # 890 ... 1700 ; freq 0  = 890
        # 920 - 1100 ; firstF    = 920
        # (950 - 920)/2.5 = ?? 
        # 950 - 890)/2.5 = ... jj
        #rangeFreqsList = allFreqsList[allFreqsList >= startFreq]
        #rangeFreqsList = rangeFreqsList[rangeFreqsList <= stopFreq]
        # A list of indexes for all cube channels in range that will hold data.
        # Expl: ( 901e6 [Hz] - 890e6 [Hz] ) // 2.5e6 [Hz] = 4 [listIndex]
        channelIndexList = [
            int((freq - firstFreq) // conf.input.outputChanBandwidth) for freq in rangeFreqsList
        ]
        channelIndexSet = set(channelIndexList)
        print(channelIndexSet)
        return channelIndexSet

    rangedChannelIndexSet = set()
    firstFreq = get_firstFreq(conf)
    for freqRange in conf.input.freqRanges:
        print(freqRange)
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

def get_unflagged_channelList(conf):
    channelList = []
    channelIndexBoolList = get_unflagged_channelIndexBoolList(conf)
    for i, channelBool in enumerate(channelIndexBoolList):
        if channelBool:
            channelList.append(i+1)
    return channelList

def get_basename_from_path(filepath):
    # remove "/" from end of path
    basename = filepath.strip("/")
    # get basename frompath
    basename = os.path.basename(basename)
    # remove file extension
    basename = os.path.splitext(basename)[0]
    return basename

# HELPER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def write_user_config_input(args):
    '''
    '''
    info(f"Writing user input to file: {args}, {FILEPATH_CONFIG_USER}")
    configString = "# TODO short discription.\n"
    configString += "# - - - - - - - - - - - - - - - - -\n\n"
    configString += "[input]\n"
    configInputStringArray = []
    with open(FILEPATH_CONFIG_USER, 'w') as f:
        for key, value in args.items():
            if key == "inputMS":
                configInputStringArray.append("basename" + " = " + get_basename_from_path(value))
            configInputStringArray.append(key + " = " + value)
        configString += "\n".join(configInputStringArray)
        f.write(configString)

def append_user_config_data(data):
    '''
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
    # split and tclean
    basename = "cube_split_and_tclean"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': "1-" + str(len(conf.data.predictedOutputChannels)) + "%30",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}'
    write_sbtach_file(filename, command, sbatchDict)

    # buildcube
    basename = "cube_buildcube"
    filename = basename + ".sbatch"
    info(f"Writing sbtach file: {filename}")
    sbatchDict = {
            'array': "1-1%1",
            'job-name': basename,
            'output': "logs/" + basename + "-%A-%a.out",
            'error': "logs/" + basename + "-%A-%a.err",
            'cpus-per-task': 16,
            'mem': "200GB",
            }
    command = '/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python3 ' + basename + '.py'
    write_sbtach_file(filename, command, sbatchDict)

    # ior flagging
    basename = "cube_ior_flagging"
    filename = basename + ".sbatch"
    info("Writing sbtach file: {0}".format(filename))
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
    info("Writing sbtach file: {0}".format(filename))
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
    info("Writing sbtach file: {0}".format(filename))
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
        shutil.copyfile(os.path.join(FILEPATH_PACKAGE, script), script)


@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx):
    '''
    TODO: I made click super generic which is nice for development but we may
    want to change this for production.
    '''
    # get the click args in dot dotation
    args = DotMap(get_dict_from_click_args(ctx.args))
    info("Scripts arguments: {0}".format(args))

    # data: values derived from the measurement set like valid channels
    data = {}
    write_user_config_input(args)
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)

    data['predictedOutputChannels'] = get_unflagged_channelList(conf)
    data['fieldnames'] = get_fieldnames(conf)
    append_user_config_data(data)
    # reload conf after data got appended to user conf
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)

    create_directories(conf)

    write_all_sbatch_files(conf)

    copy_runscripts(conf)


if __name__ == '__main__':
    main()
