#!python3
'''
------------------------------------------------------------------------------

------------------------------------------------------------------------------
Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
Inspired by: https://github.com/idia-astro/image-generator

Lennart Heino
------------------------------------------------------------------------------
'''

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import numpy as np
import sys
import logging
import datetime
import argparse
import os
import shutil
from logging import info, error

import click

import casatasks 

from mightee_pol.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from mightee_pol.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, get_firstFreq, get_basename_from_path, SEPERATOR, SEPERATOR_HEAVY

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)


# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# QUICKFIX

#Otherwise casa log files get confused
import functools
import inspect
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

# QUICKFIX
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #



def delete_temporary_files(conf):
    '''
    TODO: Find a better indicator than the hdf5 file for a sucessfull run.
    Also, think about how to arrange the report script an the cleanup.
    TODO: handle exception if directory is already deleted.
    '''
    run_success = False
    pathCubeHdf5 =  os.path.join(os.path.join(conf.input.dirHdf5Output, conf.input.basename + conf.env.extCubeHdf5))
    pathCubeSmoothedHdf5 =  os.path.join(os.path.join(conf.input.dirHdf5Output, conf.input.basename + conf.env.extCubeHdf5))
    if os.path.isfile(pathCubeHdf5):
        run_success = True
        info(f"Found file: {pathCubeHdf5}")
    else:
        error(f"File not found: {pathCubeHdf5}")

    if conf.input.smoothbeam:
        if run_success and os.path.isfile(pathCubeSmoothedHdf5):
            run_success = True
            info(f"Found file: {pathCubeSmoothedHdf5}")
        else:
            run_success = False
            error(f"File not found: {pathCubeSmoothedHdf5}")

    level = int(conf.input.cleanup)
    if run_success:
        info(f"Files found. Assuming the run went through sucessfully.")
        info(f"Deleting temporary files according to --cleanup flag.")
        if level == 0:
            info(f"Cleanup flag: --cleanup {level}. Not deleting any files.")
        elif level == 1:
            info(f"Cleanup flag: --cleanup {level}. Deleting directory {conf.env.dirVis}.")
            shutil.rmtree(conf.env.dirVis)
        elif level == 2:
            info(f"Cleanup flag: --cleanup {level}. Deleting directory {conf.env.dirVis} and {conf.env.dirImages}.")
            shutil.rmtree(conf.env.dirVis)
            shutil.rmtree(conf.env.dirImages)
    else:
        error("Files not found. Assuming run did not run through without errors. Not deleting temporary files.")

    if level == 0:
        info(f"Cleanup level {level}. Not deleting any temporary files.")

@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx):

    args = DotMap(get_dict_from_click_args(ctx.args))
    info("Scripts arguments: {0}".format(args))

    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    info("Scripts config: {0}".format(conf))

    delete_temporary_files(conf)


if __name__ == "__main__":
    main()
