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


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# INPUT
# !!! Also have a look at the QUICKFIX section

# directory with fits images per channel for Stokes IQUV.
DIR_IMAGES = "images/"

PATHLIST_STOKES_IQUV = sorted(glob(DIR_IMAGES + "*image.fits"))
PATHLIST_STOKES_FIRSTDATA = PATHLIST_STOKES_IQUV[0]

OBJECT_NAME = os.path.basename(PATHLIST_STOKES_FIRSTDATA.split(".")[0])
CUBE_NAME = "cube." + OBJECT_NAME + ".fits"

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
FILEPATH_STATISTICS = CUBE_NAME.replace(".fits", ".statistics.tab")

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

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# QUICKFIX
# If some channels are already flagged one might endup with gaps in the channel
# number of the tclean output fits files

HIGHEST_CHANNEL = 335
for i in range(1, HIGHEST_CHANNEL + 1):
    channelMarker = MARKER_CHANNEL + "{:03d}".format(i) + "."
    if channelMarker in ".".join(PATHLIST_STOKES_IQUV):
        pass
    else:
        missing = re.sub(r'\.chan[0-9]{3}\.', channelMarker, PATHLIST_STOKES_IQUV[0])
        PATHLIST_STOKES_IQUV.append(missing)

PATHLIST_STOKES_IQUV = sorted(PATHLIST_STOKES_IQUV)

#print(PATHLIST_STOKESI)

# QUICKFIX
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def get_and_add_custom_header(header):
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
    info("Getting header for data cube from: %s", PATHLIST_STOKES_FIRSTDATA)
    with fits.open(PATHLIST_STOKES_FIRSTDATA, memmap=True) as hud:
        header = hud[0].header
        # Optional: Update the header.
        header["OBJECT"] = OBJECT_NAME
        header["NAXIS3"] = len(PATHLIST_STOKES_IQUV)
        header["CTYPE3"] = ("FREQ", "")
    return header


def make_empty_image():
    """
    Generate an empty dummy fits data cube.

    The data cube dimensions are derived from the channel fits images. The
    resulting data cube can exceed the machine's RAM.

    """
    info(SEPERATOR)
    info("Getting image dimension for data cube from: %s", PATHLIST_STOKES_FIRSTDATA)
    with fits.open(PATHLIST_STOKES_FIRSTDATA, memmap=True) as hud:
        xdim, ydim = np.squeeze(hud[0].data).shape[-2:]
    info("X-dimension: %s", xdim)
    info("Y-dimension: %s", ydim)

    info(
        "Getting channel dimension Z for data cube from number of entries in PATHLIST_STOKESI."
    )
    zdim = len(PATHLIST_STOKES_IQUV)
    info("Z-dimension: %s", zdim)

    info("Assuming full Stokes for dimension W.")
    wdim = 4
    info("W-dimension: %s", wdim)

    dims = tuple([xdim, ydim, zdim, wdim])

    # create header

    dummy_dims = tuple(1 for d in dims)
    dummy_data = np.zeros(dummy_dims, dtype=np.float32)
    hdu = fits.PrimaryHDU(data=dummy_data)

    header = hdu.header
    header = get_and_add_custom_header(header)
    for i, dim in enumerate(dims, 1):
        header["NAXIS%d" % i] = dim

    header.tofile(CUBE_NAME, overwrite=True)

    # create full-sized zero image

    header_size = len(
        header.tostring()
    )  # Probably 2880. We don't pad the header any more; it's just the bare minimum
    data_size = np.product(dims) * np.dtype(np.float32).itemsize
    # This is not documented in the example, but appears to be Astropy's default behaviour
    # Pad the total file size to a multiple of the header block size
    block_size = 2880
    data_size = block_size * ((data_size // block_size) + 1)

    with open(CUBE_NAME, "rb+") as f:
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


def fill_cube_with_images():
    """
    Fills the empty data cube with fits data.


    """
    info(SEPERATOR)
    info("Opening data cube: %s", CUBE_NAME)
    hudCube = fits.open(CUBE_NAME, memmap=True, mode="update")
    dataCube = hudCube[0].data

    rmsDict = {}
    rmsDict["rmsI"] = []
    rmsDict["rmsV"] = []
    for i, filePathFits in enumerate(PATHLIST_STOKES_IQUV):
        quickSwitch = False
        print(i)
        print(PATHLIST_STOKES_IQUV[i])
        #print("---------------")
        #print(PATHLIST_STOKES_IQUV)
        info("Trying to open fits file: %s", PATHLIST_STOKES_IQUV[i])
        # Switch
        stokesVflag = False

        info(SEPERATOR)
        # Try to open file. If channel doesn't exists flag channel
       # try:
        try:
            hud = fits.open(PATHLIST_STOKES_IQUV[i], memmap=True)


            stokesV = hud[0].data[3, 0, :, :]
            checkedArray, std = check_rms(stokesV)
            rmsDict["rmsV"].append(std)
            dataCube[3, i, :, :] = checkedArray
            if np.isnan(np.sum(checkedArray)):
                stokesVflag = True
            quickSwitch = True
        except:
            info("Flagging channel, file not found: %s", PATHLIST_STOKES_IQUV[i])
            stokesVflag = True
            rmsDict["rmsV"].append(0)

        if not stokesVflag:
            stokesI = hud[0].data[0, 0, :, :]
            std = get_std_via_mad(stokesI)
            rmsDict["rmsI"].append(std)
            dataCube[0, i, :, :] = stokesI

            stokesQ = hud[0].data[1, 0, :, :]
            dataCube[1, i, :, :] = stokesQ

            stokesU = hud[0].data[2, 0, :, :]
            dataCube[2, i, :, :] = stokesU

        if stokesVflag:
            info(
                "Stokes V RMS noise of %s [uJy/beam] 0 or above RMS_THRESHOLD of %s [uJy/beam]. Flagging Stokes IQUV.",
                str(round(rmsDict["rmsV"][-1] * 1e6, 2)),
                str(round(RMS_THRESHOLD * 1e6, 3)),
            )
            dataCube[0, i, :, :] = np.nan
            dataCube[1, i, :, :] = np.nan
            dataCube[2, i, :, :] = np.nan
            dataCube[3, i, :, :] = np.nan

        if quickSwitch:
            hud.close()


    hudCube.close()
    if WRITE_STATISTICS_FILE:
        write_statistics_file(rmsDict)


if __name__ == "__main__":
    # start timestamp
    info(SEPERATOR)
    TIMESTAMP_START = datetime.datetime.now()
    info("START script at: %s", TIMESTAMP_START)
    info(SEPERATOR)

    # call methods
    make_empty_image()
    fill_cube_with_images()
    #testList = [978, 10, 10, 10, 2, 37, 10, np.nan, 100, 300, 10, 10, 10 ,10 ,10, 20, 21, 10, 10, 10]
    #get_flaggedIndexList_by_ior(testList)

    # end timestamp
    TIMESTAMP_END = datetime.datetime.now()
    TIMESTAMP_DELTA = TIMESTAMP_END - TIMESTAMP_START
    info(SEPERATOR)
    info("END script at %s in %s", str(TIMESTAMP_END), str(TIMESTAMP_DELTA))
    info(SEPERATOR)
