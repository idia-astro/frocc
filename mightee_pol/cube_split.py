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
from logging import info, error

import click

import casatasks 

from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
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


def call_split(channelNumber, conf, msIdx):
    '''
    '''
    info(f"Starting CASA split for MS and channelNumber: {conf.input.inputMS[msIdx]}, {channelNumber}")

    firstFreq = get_firstFreq(conf)
    # TODO: bug with bandwidth?
    startFreq = str(int(firstFreq) + int(conf.input.outputChanBandwidth) * (channelNumber - 1))
    stopFreq = str(int(firstFreq) + int(conf.input.outputChanBandwidth) * channelNumber)
    spw = "*:" + startFreq + "~" + stopFreq + "Hz"
    # generate outputMS filename from INPUT_MS filename
    outputMS = (
        conf.env.dirVis
        + get_basename_from_path(conf.input.inputMS[msIdx])
        + conf.env.markerChannel
        + str(channelNumber).zfill(3)
        + ".ms"
    )
    info(f"CASA split output file: {outputMS}")
    casatasks.split(
        vis=conf.input.inputMS[msIdx],
        outputvis=outputMS,
        observation=conf.input.observation,
        field=str(conf.data.chosenField),
        spw=spw,
        keepmms=False,
        datacolumn=conf.input.datacolumn,
    )


def get_channelNumber_from_slurmArrayTaskId(slurmArrayTaskId, conf):
    '''
    '''
    # concatinate all channel lists for each ms in one list
    concatChanList = []
    for chanList in conf.data.predictedOutputChannels:
        concatChanList += chanList
    return concatChanList[int(slurmArrayTaskId)-1]

def get_msIdx_from_slurmArrayTaskId(slurmArrayTaskId, conf):
    '''
    '''
    msIdx = 0
    tmpMSchannelLength = len(conf.data.predictedOutputChannels[0])
    while int(slurmArrayTaskId) > tmpMSchannelLength:
        msIdx += 1
        tmpMSchannelLength += len(conf.data.predictedOutputChannels[msIdx])
    return msIdx


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

    channelNumber = get_channelNumber_from_slurmArrayTaskId(args.slurmArrayTaskId, conf)

    # TODO: help: re-definition of casalog not working.
    # casatasks.casalog.setcasalog = conf.env.dirLogs + "cube_split_and_tclean-" + str(args.slurmArrayTaskId) + "-chan" + str(channelNumber) + ".casa"

    msIdx = get_msIdx_from_slurmArrayTaskId(args.slurmArrayTaskId, conf)
    call_split(channelNumber, conf, msIdx)


if __name__ == "__main__":
    main()
