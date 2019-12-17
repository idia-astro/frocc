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
# INPUT

# TODO: marry this with argparse
# Important: go to call_tclean to change the tclean parameters

# INPUT_MS: The input measurement data set to generate the data cube from
INPUT_MS = "1538856059_sdp_l0.full_1284.full_pol.J0521+1638.noXf.ms"

# START_FREQ_Hz in [ Hz ]: everything below this frequency gets flagged
START_FREQ_Hz = 890e6

# FREQ_RESOLUTION_Hz in [ Hz ]: final channel width of the cube data
FREQ_RESOLUTION_Hz = 2.5e6

# OBSERVATION: The observation ID
OBSERVATION = "0"

# FIELD: The field ID
FIELD = "0"

# FILEPATH_CLEANMASK: clean mask for CASA tclean TODO
FILEPATH_CLEANMASK = ""

# INPUT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

DIR_LOGS = "logs/"
DIR_IMAGES = "images/"
DIR_VIS = "vis/"
LIST_DIRECTORIES = [DIR_LOGS, DIR_IMAGES, DIR_VIS]

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# HELPER

def get_all_freqsList():
    """
    Get all the frequencies of all the sub-channels in each spw.
    """
    allFreqsList = np.array([])
    msmd.open(INPUT_MS)
    #print(msmd.chanfreqs(1) + msmd.chanwidths(1))
    for spw in range(0, msmd.nspw()):
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) + msmd.chanwidths(spw)))
        allFreqsList = np.append(allFreqsList, (msmd.chanfreqs(spw) - msmd.chanwidths(spw)))
    return allFreqsList


def get_unflagged_channelIndexBoolList():
    '''
    '''
    allFreqsList = get_all_freqsList()
    # A list of indexes for all cube channels that will hold data.
    # Expl: ( 901e6 [Hz] - 890e6 [Hz] ) // 2.5e6 [Hz] = 4 [listIndex]
    channelIndexList = [
        int((freq - START_FREQ_Hz) // FREQ_RESOLUTION_Hz) for freq in allFreqsList
    ]
    # remove negative values
    channelIndexList = np.array(channelIndexList)
    channelIndexList = channelIndexList[channelIndexList >= 0]
    maxChannelIndex = max(channelIndexList)
    # True if cube channel holds data, otherwise False
    channelIndexBoolList = []
    for ii in range(0, maxChannelIndex + 1):
        if ii in channelIndexList:
            channelIndexBoolList.append(True)
        else:
            channelIndexBoolList.append(False)
    return channelIndexBoolList


def parse_args():
    '''
    Parse arguments into this script.
    '''

    # TODO: more argparse
    parser = argparse.ArgumentParser(
        #prog=sys.argv[0],
        description="Create spectro-polarimetric output MS from input MS. Runs CASA split and tclean.",
    )

    parser.add_argument(
        "--slurmJobId", required=True, type=int, help="SLURM_JOB_ID, has to start with a value greater 0."
    )

    args, unknown = parser.parse_known_args()

    return args


channelIndexBoolList = get_unflagged_channelIndexBoolList()
# HELPER
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def check_validity(args):
    """
    """
    return channelIndexBoolList[args.slurmJobId - 1]


def create_directories():
    """
    """
    for directory in LIST_DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory)


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


def process(args):
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

    process(args)

    TIMESTAMP_END = datetime.datetime.now()
    TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
    info(SEPERATOR)
    info("END script in {0}".format(str(TIMESTAMP_DELTA)))
    info(SEPERATOR)
    info(SEPERATOR)
