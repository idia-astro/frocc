#!python3
"""
------------------------------------------------------------------------------
This script generates an empty dummy 4 dimensional data cube in fits format.
After the initialisation this cube gets filled with fits image data. The
cube header gets updated from the first image in PATHLIST_STOKES_IQUV.
This script can be used to generate fits data cubes of sizes that exceeds the
machine's RAM (tested with 234 GB RAM and 335 GB cube data).

Please adjust the INPUT section in this script to your needs.

The data in directory `images` is test data and consists of Gaussian noise only.  

------------------------------------------------------------------------------
Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
Inspired by: https://github.com/idia-astro/image-generator

Lennart Heino
------------------------------------------------------------------------------
"""

import itertools
import logging
from logging import info, error
import os
import csv
import datetime
from glob import glob
import re
import sys

import numpy as np
from astropy.io import fits

from lhelpers import get_channelNumber_from_filename, get_config_in_dot_notation
from setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# INPUT
# !!! Also have a look at the QUICKFIX section


# FLAGGING
FLAG_METHOD = "threshold" # threshold, ior (iterative outlier rejection)
# flag data that is above the RMS noise estimate from Stokes V. Set is to a high
# value for no flagging
RMS_THRESHOLD = 20000000  # in [uJy/beam]
RMS_THRESHOLD = RMS_THRESHOLD * 1e-6  # to [Jy/beam], don't change this!

# Set a list of channel indexes that should be flagged manually, channel index
# corresponds to the index in PATHLIST_STOKES{I,Q,U,V}.
LIST_MANUAL_FLAG_BY_INDEX = []

IOR_LIMIT_SIGMA = 4 # n sigma over median

# Outputs a statistics file with estimates for RMS noise in Stokes I and V
WRITE_STATISTICS_FILE = False
#FILEPATH_STATISTICS = CUBE_NAME.replace(".fits", ".statistics.tab")

# INPUT
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

MARKER_CHANNEL = ".chan"

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def get_and_add_custom_header(header, zdim, conf):
    """
    Gets header from fits file and updates the cube header.


    Parameters
    ----------
    header: astroy.io.fits header
       The header class that gets updated

    Returns
    -------
    header: astroy.io.fits header
       The header class that was updated

    """
    info(SEPERATOR)
    lowestChannelFitsfile = sorted(glob(conf.env.dirImages + "*image.fits"))[0]
    info("Getting header for data cube from: %s", lowestChannelFitsfile)
    with fits.open(lowestChannelFitsfile, memmap=True) as hud:
        header = hud[0].header
        # Optional: Update the header.
        header["OBJECT"] = str(conf.data.fieldnames)
        header["NAXIS3"] = int(zdim)
        header["CTYPE3"] = ("FREQ", "")
    return header


def make_empty_image(conf):
    """
    Generate an empty dummy fits data cube.

    The data cube dimensions are derived from the channel fits images. The
    resulting data cube can exceed the machine's RAM.

    """
    channelFitsfileList = sorted(glob(conf.env.dirImages + "*image.fits"))
    lowestChannelFitsfile = channelFitsfileList[0]
    highestChannelFitsfile = channelFitsfileList[-1]
    info(SEPERATOR)
    info("Getting image dimension for data cube from: %s", lowestChannelFitsfile)
    with fits.open(lowestChannelFitsfile, memmap=True) as hud:
        xdim, ydim = np.squeeze(hud[0].data).shape[-2:]
    info("X-dimension: %s", xdim)
    info("Y-dimension: %s", ydim)

    info(
        "Getting channel dimension Z for data cube from number of entries in PATHLIST_STOKESI."
    )
    # parse highest channel from fits file to get cube z dimension
    zdim = int(get_channelNumber_from_filename(highestChannelFitsfile, conf.env.markerChannel))
    info("Z-dimension: {0}".format(zdim))

    info("Assuming full Stokes for dimension W.")
    wdim = 4
    info("W-dimension: %s", wdim)

    dims = tuple([xdim, ydim, zdim, wdim])

    # create header

    dummy_dims = tuple(1 for d in dims)
    dummy_data = np.ones(dummy_dims, dtype=np.float32) * np.nan
    hdu = fits.PrimaryHDU(data=dummy_data)

    header = hdu.header
    header = get_and_add_custom_header(header, zdim, conf)
    for i, dim in enumerate(dims, 1):
        header["NAXIS%d" % i] = dim

    cubeName = "cube." +  os.path.basename(lowestChannelFitsfile.split(".")[0]) + ".fits"

    header.tofile(cubeName, overwrite=True)

    # create full-sized zero image

    header_size = len(
        header.tostring()
    )  # Probably 2880. We don't pad the header any more; it's just the bare minimum
    data_size = np.product(dims) * np.dtype(np.float32).itemsize
    # This is not documented in the example, but appears to be Astropy's default behaviour
    # Pad the total file size to a multiple of the header block size
    block_size = 2880
    data_size = block_size * ((data_size // block_size) + 1)

    cubeName = "cube." +  os.path.basename(lowestChannelFitsfile.split(".")[0]) + ".fits"

    with open(cubeName, "rb+") as f:
        f.seek(header_size + data_size - 1)
        f.write(b"\0")


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
    # std = round(std, 3)
    info("Got std via mad [uJy/beam]: %s ", round(std * 1e6, 2))
    return std


def check_rms(npArray):
    """
    Check if the Numpy Array is below RMS_THRESHOLD and above 1e-6 uJy/beam.

    If the Numpy Array is not within the range it gets assigned to not a number
    (np.nan).

    Parameters
    ----------
    npArray: numpy.array
       The numpy array to check

    Returns
    -------
    [npArray, std]: list with numpy.array and float
       List of length 2 with  the Numpy Array and the Standard Deviation

    """
    std = get_std_via_mad(npArray)
    if (std > RMS_THRESHOLD):
        npArray = np.nan
    return [npArray, std]


def write_statistics_file(statsDict):
    """
    Takes the dictionary with Stokes I and V RMS noise and writes it to a file.

    Parameters
    ----------
    rmdDict: dict of lists with floats
       Dictionary with lists for Stokes I and V rms noise

    """
    legendList = ["rmsStokesI [uJy/beam]", "rmsStokesV [uJy/beam]",  "frequency [MHz]"]
    info("Writing statistics file: %s", FILEPATH_STATISTICS)
    with open(FILEPATH_STATISTICS, "w") as csvFile:
        writer = csv.writer(csvFile, delimiter="\t")
        csvData = [legendList]
        for i, entry in enumerate(statsDict["rmsI"]):
            rmsI = round(statsDict["rmsI"][i] * 1e6, 4)
            rmsV = round(statsDict["rmsV"][i] * 1e6, 4)
            flagged = statsDict['flagged'][i] # TODO: fix this
            maxI = round(statsDict["maxI"][i] * 1e6, 4)
            freq = round(statsDict["freq"][i] * 1e-6, 4)
            csvData.append([rmsI, rmsV, freq])
        writer.writerows(csvData)


def flag_channel_by_indexList(indexList, dataCube):
    """
    Flaggs alls channels in fits data cube by indexList. TODO: write better


    """
    indexList + LIST_MANUAL_FLAG_BY_INDEX
    for i in indexList:
        print(i)
        info("Fagging channel index %s, which corresponds to the following file (and Stokes QUV respectively): %s", i, PATHLIST_STOKESI[i])
        dataCube[0, i, :, :] = np.nan
        dataCube[1, i, :, :] = np.nan
        dataCube[2, i, :, :] = np.nan
        dataCube[3, i, :, :] = np.nan
    return dataCube


def get_flaggedList_by_indexList(indexList):
    flaggedList = []
    for i, filePathFits in enumerate(PATHLIST_STOKESI):
        if i in indexList:
            flaggedList.append(True)
        else:
            flaggedList.append(False)
    return flaggedList


def get_flaggedIndexList_by_ior(rmsList):
    outlierIndexList = []
    outlierSwitch = True
    while outlierSwitch:
        outlierSwitch = False
        for i, rms in enumerate(rmsList):
            medianRMS = np.nanmedian(rmsList)
            nanStdOfRMS = np.nanstd(rmsList)
            if rms > (medianRMS + IOR_LIMIT_SIGMA * nanStdOfRMS):
                outlierIndexList.append(i)
                rmsList[i] = np.nan
                outlierSwitch = True
    return outlierIndexList


def fill_cube_with_images(conf):
    """
    Fills the empty data cube with fits data.


    """
    # TODO: make this less ambigious cube.*.fits
    cubeName = glob("cube.*.fits")[0]
    info(SEPERATOR)
    info("Opening data cube: %s", cubeName)
    print(cubeName)
    hudCube = fits.open(cubeName, memmap=True, mode="update")
    dataCube = hudCube[0].data

    rmsDict = {}
    rmsDict["rmsI"] = []
    rmsDict["rmsV"] = []
    channelFitsfileList = sorted(glob(conf.env.dirImages + "*image.fits"))
    for channelFitsfile in channelFitsfileList:
        idx = int(get_channelNumber_from_filename(channelFitsfile, conf.env.markerChannel)) - 1
        quickSwitch = False
        info("Trying to open fits file: {0}".format(channelFitsfile))
        # Switch
        stokesVflag = False

        info(SEPERATOR)
        # Try to open file. If channel doesn't exists flag channel
       # try:
        try:
            hud = fits.open(channelFitsfile, memmap=True)


            stokesV = hud[0].data[3, 0, :, :]
            checkedArray, std = check_rms(stokesV)
            rmsDict["rmsV"].append(std)
            dataCube[3, idx, :, :] = checkedArray
            if np.isnan(np.sum(checkedArray)):
                stokesVflag = True
            quickSwitch = True
        except:
            info("Flagging channel, file not found: %s", channelFitsfile)
            stokesVflag = True
            rmsDict["rmsV"].append(0)

        if not stokesVflag:
            stokesI = hud[0].data[0, 0, :, :]
            std = get_std_via_mad(stokesI)
            rmsDict["rmsI"].append(std)
            dataCube[0, idx, :, :] = stokesI

            stokesQ = hud[0].data[1, 0, :, :]
            dataCube[1, idx, :, :] = stokesQ

            stokesU = hud[0].data[2, 0, :, :]
            dataCube[2, idx, :, :] = stokesU

        if stokesVflag:
            info(
                "Stokes V RMS noise of %s [uJy/beam] 0 or above RMS_THRESHOLD of %s [uJy/beam]. Flagging Stokes IQUV.",
                str(round(rmsDict["rmsV"][-1] * 1e6, 2)),
                str(round(RMS_THRESHOLD * 1e6, 3)),
            )
            dataCube[0, idx, :, :] = np.nan
            dataCube[1, idx, :, :] = np.nan
            dataCube[2, idx, :, :] = np.nan
            dataCube[3, idx, :, :] = np.nan

        if quickSwitch:
            hud.close()


    hudCube.close()
    if WRITE_STATISTICS_FILE:
        write_statistics_file(rmsDict)


def main():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    info("Scripts config: {0}".format(conf))

    make_empty_image(conf)
    fill_cube_with_images(conf)



if __name__ == "__main__":
    TIMESTAMP_START = datetime.datetime.now()
    info(SEPERATOR)
    info(SEPERATOR)
    info("STARTING script.")
    info(SEPERATOR)

    main()

    TIMESTAMP_END = datetime.datetime.now()
    TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
    info(SEPERATOR)
    info("END script in {0}".format(str(TIMESTAMP_DELTA)))
    info(SEPERATOR)
    info(SEPERATOR)
