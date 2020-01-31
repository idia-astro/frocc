'''
Convinience functions and classes.
'''

import configparser
import datetime
import ast
import logging
import functools
import numpy as np
import inspect
from logging import info, error

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
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


def get_config_in_dot_notation(templateFilename="default_config.template", configFilename="default_config.txt"):
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


def write_sbtach_file(filename, command, sbatchDict={}):
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
    with open(filename, 'w') as f:
        sbatchScript = "#!/bin/bash"
        for key, value in defaultDict.items():
            sbatchScript += "\n#SBATCH --" + key + "=" + str(value)

        sbatchScript += "\n\ncat /etc/hostname" 
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

