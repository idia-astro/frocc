#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE_ORIGINAL
from mightee_pol.lhelpers import DotMap, get_dict_from_click_args
from mightee_pol.config import SPECIAL_FLAGS
import sys
import os
'''
-------------------------------------------------------------------------------
-------------------------------------------------------------------------------
'''
USAGE='''
 meerkat-pol Usage
 ==================
 
 1. Usage
 --------
 1. `meerkat-pol --createConfig --inputMS <path to input.ms>`
 2. `meerkat-pol --createScripts [--copyScripts]
 3. `meerkat-pol --start`
 
 2. In one command
 -----------------
 `meerkat-pol --createConfig --inputMS <path to input.ms> --createScripts --start`
 
 3. More advanced
 ----------------
 `meerkat-pol --inputMS "/my/data/input1.ms, /my/data/input2.mms" --freqRanges '["900-1000", "1300-1500", "1600-1650"]' --imsize 1024 --niter 500 --threshold 0.0001 --smoothbeam 15arcsec --createConfig --createScripts --start`

 4. Show the status
 ------------------
 merkat-pol --status

 5. Canel slurm jobs
 -------------------
 merkat-pol --cancel

 6. Further help
 ---------------
 merkat-pol --readme
 merkat-pol --help
'''

README='''
 meerkat-pol Readme
 ==================
 
 1. Installation
 ---------------
 
 ### Via source:
 `source /users/lennart/software/sourcePipeline-stable.sh`
 
 ### Via pip (experimental):
 1. `git clone git@github.com:idia-astro/mightee-pol.git`
 2. `cd mightee-pol`
 3. `pip install --user .`
 
 
 2. Implementation
 -----------------
 
 `merkat-pol` takes input measurement set (ms) data and parameters to create
 channelized data cube in Stokes IQUV.  
 First CASA `split` is run to split out visibilities from the input ms into
 visibilities of the aimed resolution in frequency. Then `tclean` runs on each
 of these ms separately and creates `.fits`-files for each channel. Next, the
 channel files are put into a data cube. The cube is analysed with an iterative
 outlier rejection which detects strongly diverging channels by measuring the
 RMS in Stokes V by fitting a third order polynomial. Bad channels get flagged
 and the cube `.fits`-file is converted into a `.hdf5`-file.  
 The aforementioned is realized through the following scripts:
 `cube_split.py, cube_tclean.py, cube_buildcube.py, cube_ior_flagging.py`
 
 ------------------------------------------------------------------------------
 
 The input of parameters and setting can be controlled via 3 methods:
 
 1. Command line argument: `meerkat-pol --inputMS "myData.ms"`
 After calling `meerkat-pol` with `--createConfig` all settings are written to
 `default_config.txt`. (All valid flags can be found in
 `.default_config.template` under the `[input]` section).
 
 2. Standard configuration file: `default_config.txt`
 After creating `default_config.txt` via `meerkat-pol ... ... --createConfig`
 it can be revised. All parameters in here overwrite the ones in
 `.default_config.template`. Do not change anything under the section `[data]`.
 
 3. Fallback configuration file: `.default_config.template
 The pipeline falls back to the values in this file if they have not been
 specified via one of the previous way. It is also a place where one can lookup
 explanations for valid flags for `meerkat-pol`. It also includes the section
 `[env]` which can not be controlled via command line flags.
 
 ------------------------------------------------------------------------------
 
 When calling `meerkat-pol --createScripts` `default_config.txt` and
 `.default_config.template` are read and the python and slurm files are copied
 to the current directory. The script also tries to calculate the optimal
 number of slurm taks depending on the input ms spw coverage.
 
 The last step `meerkat-pol --start` submits the slurm files in a dependency
 chain. Caution: CASA does not always seem to report back its failure state in
 a correct way. Therefore, the slurm flag `--dependency=afterany:...` is
 chosen, which starts the next job in the chain even if the previous one has
 failed.
 
 ### Logging
 TODO: It's tricky, CASA's logger gets in the way.

 
 3. Known issues
 ---------------
 - About 2% of cube channels show a differend frequency width

 
-------------------------------------------------------------------------------
 
  Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
  Inspired by: https://github.com/idia-astro/image-generator
  
  Lennart Heino
 
-------------------------------------------------------------------------------
'''

def get_config_dictList():
    '''
    '''
    with open(FILEPATH_CONFIG_TEMPLATE_ORIGINAL, 'r') as f:
        configDictList = []
        configList = [ line.strip() for line in f.readlines() ]
        # only get the [input] section
        inputList = configList[configList.index("[input]")+1:configList.index("[env]")]
        inputList = [ line for line in inputList if line.startswith("#") or ( not line.startswith("#") and line.find("=") > 0) ]
        keywords = ("# DESCRIPTION:", "# TYPE:", "# TYPE-COMMENT:", "# EXAMPLE:")
        configDict = {}
        lastKey = ""
        for line in inputList:
            if line.startswith(keywords):
                key, value = line.split(":", 1)
                key = key[2:]
                configDict[key] = value.strip()
                lastKey = key
            elif line.startswith("#") and lastKey:
                configDict[lastKey] += line[1:].rstrip()
            elif not line.startswith("#") and line.find("=") > 0:
                configDict['DEFAULT'] = line
                configDict['FLAG'] = f'--{line.split("=",1)[0].strip()}'
                configDictList.append(configDict)
                configDict = {}
                lastKey = ""
    return configDictList


def check_if_flag_exists(flagList):
    '''
    TODO: filter -- and - prefix handling better
    '''
    configDictList = get_config_dictList()
    validFlags = []
    for entry in configDictList:
        validFlags.append(entry["FLAG"])
    validFlags += SPECIAL_FLAGS
    ddFlagList = [ flag for flag in flagList if flag.startswith("--") ]
    # TODO: better flag parsing
#    wrongFlags = [ flag for flag in flagList if ( not flag.startswith("--") and flag.startswith("-"))]
    wrongFlags = list(set(ddFlagList).difference(set(validFlags)))
    wrongFlags = ", ".join(wrongFlags)
    if wrongFlags:
        print(f' ERROR: Flag not recognised: {wrongFlags}')
        print()
        print(f' `meerkat-pol --help` to list all valid flags')
        sys.exit()


def check_flag_type(flagList, conf):
    configDictList = get_config_dictList()


def check_flags(flagList, conf):
    check_if_flag_exists(flagList)

def print_help():
    configDictList = get_config_dictList()
    print("meerkat-pol --help")
    for entry in configDictList:
        # get padding depending on key length
        keyLength = 0
        print(f' {entry["FLAG"]}')
        for key, value in entry.items():
            if keyLength < len(key):
                keyLength = len(key)
        for key, value in entry.items():
            # ignore FLAG
            if key != "FLAG":
                padding = (keyLength - len(key)) * " "
                line = "  "+key+": " + padding + value
                print(line)
        print()
    print(" For more usage support please read the output of:")
    print("  meerkat-pol --usage")
    print("  meerkat-pol --readme")

def print_usage():
    print(USAGE)

def print_readme():
    print(README)

def check_path_inputMS(flagList, conf):
    '''
    TODO
    '''
    print(conf.input.inputMS)
    if conf.input.inputMS:
        print("hello")
        for inputMS in conf.input.inputMS:
            if not os.path.exists(inputMS):
                print(f"ERROR: File does not exists {inputMS}")
                sys.exit()


def check_all(flagList):
    #conf = DotMap(get_dict_from_click_args(flagList))
    conf = None
    check_flags(flagList, conf)
    #check_path_inputMS(flagList, conf)
    #check_flags(conf)


def main(conf):
    print_help()

if __name__=="__main__":
    conf = ""
    main(conf)
