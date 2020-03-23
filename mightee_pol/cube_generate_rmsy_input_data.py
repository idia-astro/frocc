#!python3
# -*- coding: utf-8 -*-

import numpy as np
import logging
import csv
from numpy.polynomial.polynomial import polyfit
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib as mpl
from scipy.stats import linregress
from scipy import optimize
from astropy.io import fits
from glob import glob
import os

from scipy import *
from mightee_pol.lhelpers import get_std_via_mad, get_config_in_dot_notation, main_timer, get_firstFreq
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from logging import info, error
import subprocess


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def format_legend(item):
    # remove everything after the first [
    index = item.find('[')
    if index > 0:
        item = item[0:index]
    return item.strip()

def write_statistics_file(statsDict, conf):
    """

    Parameters
    ----------

    """
    filepathStatistics = os.path.join(conf.env.dirRMSYdata, "rmsy." + conf.input.basename + ".tab")
    info("Writing statistics file: %s", filepathStatistics)
    with open(filepathStatistics, "w") as csvFile:
        writer = csv.writer(csvFile, delimiter="\t")
        csvData = []
        for i, freq in enumerate(statsDict["frequency"]):
            maxI = round(statsDict['stokesImaxList'][i] * 1e6, 4)
            rmsI = round(statsDict['stokesVrmsList'][i] * 1e6, 4)
            maxQ = round(statsDict['stokesQmaxList'][i] * 1e6, 4)
            rmsQ = round(statsDict['stokesVrmsList'][i] * 1e6, 4)
            maxU = round(statsDict['stokesUmaxList'][i] * 1e6, 4)
            rmsU = round(statsDict['stokesVrmsList'][i] * 1e6, 4)
            csvData.append([freq, maxI, rmsI, maxQ, rmsQ, maxU, rmsU])
        writer.writerows(csvData)


def get_dict_from_tabFile(tabFile):
    allStatsDict = {}
    with open(tabFile) as f:
        lines = f.read().splitlines()
        # initialize dict
        for key in lines[0].split('\t'):
            allStatsDict[format_legend(key)] = []
        for line in lines[1:]:
            for i, key in enumerate(allStatsDict):
                allStatsDict[key].append(eval(line.split('\t')[i]))
    return allStatsDict


def get_rmsyDict_from_cube(conf):
    """
    Simple not optimized version TODO

    """
    cubeName = "cube." + conf.input.basename + ".fits"
    info(SEPERATOR)
    info("Opening data cube: %s", cubeName)
    # TODO: debug: if ignore_missing_end is not true I get an error.
    hudCube = fits.open(cubeName, memmap=True, ignore_missing_end=True, mode="update")
    dataCube = hudCube[0].data
    asd, maxIndex, width, height = shape(dataCube)
    rmsBoxSize = int(width * 0.04)
    # get pixel coordinates of max value. try first channel. If it is nan, go to next channel
    info("Trying to get x-y coordinates of highest value of Stokes I in channel.")
    for ii in range(0, maxIndex + 1):
        info(f"Trying channel: {ii + 1}")
        if not np.isnan(np.nanmax(dataCube[0, ii, :, :])):
            print(np.nanmax(dataCube[0, ii, :, :]))
            print(np.where(dataCube == np.amax(dataCube[0, ii, :, :])))
            asd, asdidx, xMaxIndex, yMaxIndex = np.where(dataCube == np.amax(dataCube[0, ii, :, :]))
            xMaxIndex = xMaxIndex[0]
            yMaxIndex = yMaxIndex[0]
            break
    info(f"Found max value at coordinates: x = {xMaxIndex}, y = {yMaxIndex}")

    freqList = []
    stokesImaxList = []
    stokesQmaxList = []
    stokesUmaxList = []
    stokesVrmsList = []

    for ii in range(0, maxIndex + 1):
        # try except, excepts by np.nan. TODO: write this cleaner
        try:
            firstFreq = get_firstFreq(conf)
            freq = firstFreq + conf.input.outputChanBandwidth * ii
            stokesImax = dataCube[0, ii, xMaxIndex, yMaxIndex]
            stokesQmax = dataCube[1, ii, xMaxIndex, yMaxIndex]
            stokesUmax = dataCube[2, ii, xMaxIndex, yMaxIndex]

            xStart = int(xMaxIndex - rmsBoxSize/2)
            xStop = int(xMaxIndex + rmsBoxSize/2)
            yStart = int(yMaxIndex - rmsBoxSize/2)
            yStop = int(yMaxIndex + rmsBoxSize/2)
            stokesVrms = get_std_via_mad(dataCube[3, ii, xStart:xStop, yStart:yStop])

            freqList.append(freq)
            stokesImaxList.append(stokesImax)
            stokesQmaxList.append(stokesQmax)
            stokesUmaxList.append(stokesUmax)
            stokesVrmsList.append(stokesVrms)
            info(f"From channel number {ii + 1} got frequency [Hz], stokesImax [uJy/beam], stokesQmax [uJy/beam], stokesUmax [uJy/beam], stokesVrms [uJy/beam]: {freq * 1e6}, {stokesImax * 1e6}, {stokesQmax * 1e6}, {stokesUmax * 1e6}, {stokesVrms * 1e6}")
        except:
            info(f"Channel is nan: {ii + 1}")

    info(SEPERATOR)
    hudCube.close()
    statsDict = dict()
    statsDict["frequency"] = freqList
    statsDict["stokesImaxList"] = stokesImaxList
    statsDict["stokesQmaxList"] = stokesQmaxList
    statsDict["stokesUmaxList"] = stokesUmaxList
    statsDict["stokesVrmsList"] = stokesVrmsList
    write_statistics_file(statsDict, conf)



@main_timer
def main():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
#    statsDict = get_dict_from_tabFile(FILEPATH_STATISTICS)
#    initialStatsDict = dict(statsDict)  # make a deep copy
    get_rmsyDict_from_cube(conf)


if __name__ == "__main__":
    main()
