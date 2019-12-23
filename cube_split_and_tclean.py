#!/opt/anaconda3/bin/python3
'''
------------------------------------------------------------------------------
Beta code

This script runs CASA split and tclean using a slurm sbatch array job.
The purpose is to generate images for each frequency channel which channel
width is set by FREQ_RESOLUTION_Hz.

In the first step check_validity() the script figures out which ranges of the
whole bandwidth hold data and therefore should be considered for imaging.

create_directories() creates the needed directories. Please note that the
"logs" directory needs to be created before running the script because the
slurm sbatch script expects this already.

call_split() splits out the visibilities for each channel (of width
FREQ_RESOLUTION_Hz) into the directory DIR_VIS.

In the last step call_tclean() the images (casa and .fits) are created in
DIR_IMAGES. The setting need for tclean need to be changed in call_tclean()
directly.

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
import os
from logging import info, error


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"


# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def call_split(args):
    startFreq = str(START_FREQ_Hz + FREQ_RESOLUTION_Hz * (args.slurmJobId - 1))
    stopFreq = str(START_FREQ_Hz + FREQ_RESOLUTION_Hz * args.slurmJobId)
    spw = "*:" + startFreq + "~" + stopFreq + "Hz"
    # generate outputMS filename from INPUT_MS filename
    outputMS = (
        DIR_VIS
        + os.path.splitext(os.path.basename(INPUT_MS))[0]
        + ".chan"
        + str(args.slurmJobId).zfill(3)
        + ".ms"
    )
    split(
        vis=INPUT_MS,
        outputvis=outputMS,
        observation=OBSERVATION,
        field=FIELD,
        spw=spw,
        keepmms=False,
        datacolumn="data",
    )
    # TODO: find better way than returning the outputMS filename
    return outputMS


def call_tclean(args, inputMS):
    '''
    '''
    imagename = DIR_IMAGES + os.path.basename(inputMS)
    tclean(
        vis=inputMS,
        imagename=imagename,
        niter=500,
        gain=0.1,
        deconvolver="clark",
        threshold=0.00001,
        imsize=500,
        cell=1.5,
        gridder="wproject",
        wprojplanes=-1,
        specmode="mfs",
        spw="",
        stokes="IQUV",
        weighting="briggs",
        robust=0.0,
        pblimit=-1,
        # mask=args.cleanmask, usemask='user',
        restoration=True,
        restoringbeam=["18arcsec"],
    )
    # export to .fits file
    outname = imagename + ".image"
    outfits = outname + ".fits"
    exportfits(imagename=outname, fitsimage=outfits, overwrite=True)


def main(args):
    if check_validity(args):
        create_directories()
        splitOutputMS = call_split(args)
        call_tclean(args, splitOutputMS)
    else:
        # TODO: tell which freq
        info("No data at this frequency.")


if __name__ == "__main__":
    TIMESTAMP_START = datetime.datetime.now()
    info(SEPERATOR)
    info(SEPERATOR)
    info("STARTING script.")
    info(SEPERATOR)

    args = parse_args()
    info("Scripts arguments: {0}".format(args))

    main(args)

    TIMESTAMP_END = datetime.datetime.now()
    TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
    info(SEPERATOR)
    info("END script in {0}".format(str(TIMESTAMP_DELTA)))
    info(SEPERATOR)
    info(SEPERATOR)
