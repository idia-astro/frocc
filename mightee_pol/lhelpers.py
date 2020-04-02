# -*- coding: utf-8 -*-
'''
Convinience functions and classes.
'''

import configparser
import datetime
import os
import ast
import functools
import numpy as np
import inspect
from astropy.io import fits
from astropy.io import fits
#from mightee_pol.logger import info, debug, error, warning

#import logging
#from logging import info, debug, error, warning
from mightee_pol.logger import *

#logging.basicConfig(
#    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
#)

SEPERATOR = "-------------------------------------------------------------------------------"
SEPERATOR_HEAVY = "==============================================================================="


class DotMap(dict):
    """
    Own implementation to convert a python dict into dot notation.
    mydict['city'] --> mydict.city
    There is a package for this but I wanted less dependencies:
    https://github.com/drgrib/dotmap

    Example:
    m = DotMap({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        super(DotMap, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v


        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(DotMap, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(DotMap, self).__delitem__(key)
        del self.__dict__[key]


def get_dict_from_click_args(argsList):
    '''
    '''
    argsDict = {}
    for item in argsList:
        if item.startswith("--"):
            lastKey = item.replace("--","")
            argsDict[lastKey] = None
        else:
            # In case one key has two values
            if not argsDict[lastKey]:
                argsDict[lastKey] = [argsDict[lastKey]].append(item)
            argsDict[lastKey] = item
    return argsDict


def get_config_in_dot_notation(templateFilename=".default_config.template", configFilename="default_config.txt"):
    '''
    '''
    config = configparser.ConfigParser(allow_no_value=True, strict=False)
    # In order to prevent key to get converted to lower case
    config.optionxform = lambda option: option
    config.read([templateFilename, configFilename])
    dot = DotMap(config._sections)
    for section in config._sections:
        setattr(dot, section, DotMap(config[section]))
        for key, value in config[section].items():
            try:
                setattr(getattr(dot, section), key, eval(value))
            except:
                # if "input.ms" is eval to Object (because of . ), treat as string
                setattr(getattr(dot, section), key, str(value))
    return dot

def get_channelNumber_from_filename(filename, marker, digits=3):
    '''
    TODO: digits=3 -> len(marker)
    '''
    markerChannelPositionEnd = int(filename.find(marker)) + len(marker)
    chanNo = filename[markerChannelPositionEnd:markerChannelPositionEnd+digits]
    return chanNo.zfill(digits)

def change_channelNumber_from_filename(filename, marker, newChanNo, digits=3):
    '''
    TODO: digits=3 -> len(marker)
    '''
    markerChannelPositionEnd = int(filename.find(marker)) + len(marker)
    chanNo = filename[markerChannelPositionEnd:markerChannelPositionEnd+digits]
    newFilename = filename.replace(marker+str(chanNo).zfill(digits), marker+str(newChanNo).zfill(digits))
    return newFilename

def main_timer(func):
    '''
    '''
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        TIMESTAMP_START = datetime.datetime.now()
        info(SEPERATOR_HEAVY)
        info(f"STARTING script: {inspect.stack()[-1].filename}")
        info(SEPERATOR)

        func(*args, **kwargs)

        TIMESTAMP_END = datetime.datetime.now()
        TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
        info(SEPERATOR)
        info(f"END script in {TIMESTAMP_DELTA}: {inspect.stack()[-1].filename}")
        info(SEPERATOR_HEAVY)
    return wrapper


def write_sbtach_file(filename, command, conf, sbatchDict={}):
    # TODO: better put this "if" to check which scripts should be created somewhere else
    if filename.replace(".sbatch", ".py") in conf.env.runScripts:
        defaultDict = {
                'array': "1-30%30",
                'nodes': 1,
                'ntasks-per-node': 1,
                'cpus-per-task': 4,
                'mem': "29GB",
                'job-name': "NoName",
                'output': "/logs/NoName-%A-%a.out",
                'error': "/logs/NoName-%A-%a.err",
                'partition': "Main",
                }
        # update default with provided dict if not empty
        if sbatchDict:
            defaultDict.update(sbatchDict)
        info(f"Writing sbtach file: {filename}")
        with open(filename, 'w') as f:
            sbatchScript = "#!/bin/bash"
            for key, value in defaultDict.items():
                sbatchScript += "\n#SBATCH --" + key + "=" + str(value)

            sbatchScript += "\n\ncat /etc/hostname" 
            sbatchScript += "\nulimit -a" 
            sbatchScript += "\n\n" + command
            f.write(sbatchScript)

#write_sbtach_file("test.sbtach", "echo hi", {'job-name': "testestest", 'hi': 3})


def get_mad(a, axis=None):
    """
    Compute *Median Absolute Deviation* of an array along given axis.

    from: https://informatique-python.readthedocs.io/fr/latest/Exercices/mad.html

    Parameters
    ----------
    a: numpy.array
       The numpy array of which MAD gets calculated from

    Returns
    -------
    mad: float
       MAD from a

    """
    # Median along given axis, but *keeping* the reduced axis so that
    # result can still broadcast against a.
    med = np.nanmedian(a, axis=axis, keepdims=True)
    mad = np.nanmedian(np.absolute(a - med), axis=axis)  # MAD along given axis
    return mad


def get_std_via_mad(npArray):
    """
    Estimate standard deviation via Median Absolute Deviation.


    Parameters
    ----------
    npArray: numpy.array
       The numpy array of which the Standard Deviation gets calculated from

    Returns
    -------
    std: float
       Standard Deviation from MAD

    """
    mad = get_mad(npArray)
    std = 1.4826 * mad
    return std


def get_firstFreq(conf):
    firstFreq = float(conf.input.freqRanges[0].split("-")[0]) * 1e6
    return firstFreq

def get_basename_from_path(filepath):
    '''
    '''
    try:
        isinstance(eval(filepath), list)
    except:
        # convert string to list, split at, strip whitespace and all back to a string again to write it to config
        filepath = str([x.strip() for x in list(filter(None, filepath.split(",")))])
    # remove "/" from end of path
    basename = eval(filepath)[0].strip("/")
    # get basename frompath
    basename = os.path.basename(basename)
    # remove file extension
    basename = os.path.splitext(basename)[0] + "." + get_timestamp()
    return basename

def get_optimal_taskNo_cpu_mem(conf):
    '''
    Tries to return an optimal resource profile (mainly for t-clean) derived
    from the image size. At the moment only a naive implementation is done.
    Scaling linear: 500px to 7500px. Have a look into .default_config.template
    '''
    def linear_fit(m, x, b):
        return m * x + b

    mMemory = (conf.env.tcleanMaxMemory - conf.env.tcleanMinMemory) / (7500 - 500)
    mCPU = (conf.env.tcleanMaxCpuCores - conf.env.tcleanMinCpuCores) / (7500 - 500)

    bMemory = (mMemory * 7500) / conf.env.tcleanMaxMemory
    bCPU = (mCPU * 7500) / conf.env.tcleanMaxCpuCores

    yMemory = int(linear_fit(mMemory, conf.input.imsize, bMemory))
    yCPU = int(linear_fit(mCPU, conf.input.imsize, bCPU))

    # calculate how many slurm tasks can be started to fit on maxSimultaniousNodes
    numberOfTasks = conf.env.tcleanMaxMemory // yMemory * conf.env.maxSimultaniousNodes
    optimalDict = {"maxTasks": numberOfTasks, "cpu": yCPU, "mem": yMemory}
    info(f"Setting tclean sbatch values based on imsize: {optimalDict}")
    return optimalDict


def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d")


def update_fits_header_of_cube(filepathCube, headerDict):
    '''
    '''
    info(f"Updating header for file: File: {filepathCube}, Update: {headerDict}")
    with fits.open(filepathCube, memmap=True, ignore_missing_end=True, mode="update") as hud:
        header = hud[0].header
        for key, value in headerDict.items():
            header[key] = value


def get_lowest_channelNo_with_data_in_cube(filepathCube):
    '''
    '''
    info(f"Getting lowest channel number which holds data in cube: {filepathCube}") 
    with fits.open(filepathCube, memmap=True) as hud:
        dataCube = hud[0].data
        maxIdx = hud[0].data.shape[1]
        for ii in range(0, maxIdx + 1):
            if np.isnan(np.sum(dataCube[0, ii, :, :])) or np.sum(dataCube[0, ii, :, :] == 0):
                continue
            else:
                chanNo = ii + 1
                return chanNo


def update_CRPIX3(filepathCube):
    '''
    Updates the frequency reference channel in the fits header, CRPIX3.
    '''
    chanNo = get_lowest_channelNo_with_data_in_cube(filepathCube)
    headerDict = {"CRPIX3": chanNo}
    info(f"Updating CRPIX3 value in fits header: {filepathCube}, {headerDict}")
    update_fits_header_of_cube(filepathCube, headerDict)

def print_starting_banner(headline):
    maxLength = len(SEPERATOR_HEAVY)
    spaceHelper = "                                                                                       "
    empty = spaceHelper[:maxLength+1]
    blank = "||" + spaceHelper
    blank = blank[:maxLength-2] + "||"
    main = blank[:int((maxLength/2.) - (len(headline)/2.))] + headline
    main = main[:maxLength-1] + blank[2:int((maxLength/2.) - (len(headline)/2.))] + " "
    main = main[:maxLength-2] + "||"
    info(empty)
    info(SEPERATOR_HEAVY)
    info(blank)
    info(main)
    info(blank)
    info(SEPERATOR_HEAVY)
    info(empty)


