#!python3
# -*- coding: utf-8 -*-
'''
------------------------------------------------------------------------------
Beta code

This script runs CASA split and tclean started through a slurm sbatch array job.
The purpose is to generate images for each frequency channel which channel
width is set by `outputChanBandwidth`.

call_split() splits out the visibilities for each channel (of width
`outputChanBandwidth`) into the directory `dirVis`.

In the last step call_tclean() the images (casa and .fits) are created in
`dirImages`.

After all the images are created you may want to run cube_buildcube.{py,sbatch}

Please adjust the INPUT section in this script to your needs.

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
from glob import glob
import os
from logging import info, error

import click

import casampi
import casatasks 

from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from mightee_pol.lhelpers import get_dict_from_click_args, DotMap, get_config_in_dot_notation, main_timer, get_firstFreq, SEPERATOR

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def call_split(channelNumber, conf):
    '''
    '''
    info("Starting CASA split for channelNumber: {0}".format(channelNumber))

    firstFreq = get_firstFreq(conf)
    # TODO: bug with bandwidth?
    startFreq = str(int(firstFreq) + int(conf.input.outputChanBandwidth) * (channelNumber - 1))
    stopFreq = str(int(firstFreq) + int(conf.input.outputChanBandwidth) * channelNumber)
    spw = "*:" + startFreq + "~" + stopFreq + "Hz"
    # generate outputMS filename from INPUT_MS filename
    outputMS = (
        conf.env.dirVis
        + conf.input.basename
        + conf.env.markerChannel
        + str(channelNumber).zfill(3)
        + ".ms"
    )
    casatasks.split(
        vis=conf.input.inputMS,
        outputvis=outputMS,
        observation=conf.input.observation,
        field=str(conf.input.field),
        spw=spw,
        keepmms=False,
        datacolumn=conf.input.datacolumn,
    )
    # TODO: find better way than returning the outputMS filename
    return outputMS


def call_tclean(channelInputMS, conf):
    '''
    '''
    info("Starting CASA tclean for input file: {0}".format(channelInputMS))
    imagename = conf.env.dirImages + os.path.basename(channelInputMS)
    casatasks.tclean(
        vis=channelInputMS,
        imagename=imagename,
        niter=conf.input.niter,
        gain=conf.input.gain,
        deconvolver=conf.input.deconvolver,
        threshold=conf.input.threshold,
        imsize=conf.input.imsize,
        cell=conf.input.cell,
        gridder=conf.input.gridder,
        wprojplanes=conf.input.wprojplanes,
        specmode=conf.input.specmode,
        spw=conf.input.spw,
        stokes=conf.input.stokes,
        weighting=conf.input.weighting,
        robust=conf.input.robust,
        pblimit=conf.input.pblimit,
        mask=conf.input.mask,
        restoration=conf.input.restoration,
        restoringbeam=[conf.input.restoringbeam],
    )
    # export to .fits file
    outname = imagename + ".image"
    outfits = outname + ".fits"
    casatasks.exportfits(imagename=outname, fitsimage=outfits, overwrite=True)


def get_channelNumber_from_slurmArrayTaskId(slurmArrayTaskId, conf):
    '''
    '''
    return conf.data.predictedOutputChannels[int(slurmArrayTaskId)-1]


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

    splitOutputMS = call_split(channelNumber, conf)
    call_tclean(splitOutputMS, conf)


if __name__ == "__main__":
    main()
