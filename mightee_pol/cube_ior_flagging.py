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

from scipy import *
from mightee_pol.lhelpers import get_std_via_mad, get_config_in_dot_notation, main_timer, update_CRPIX3, SEPERATOR
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from logging import info, error
import subprocess

IOR_LIMIT_SIGMA = 5 # n sigma over median

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)

sns.set(font_scale=1.5)
#plt.rcParams.update({'font.size': 12})
mpl.use('Agg') # Backend that doesn't need X server
mpl.rcParams['xtick.labelsize'] = 22
mpl.rcParams['ytick.labelsize'] = 22
mpl.rcParams['axes.titlesize'] = 26
sns.set_style("ticks")
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
    Takes the dictionary with Stokes I and V RMS noise and writes it to a file.

    Parameters
    ----------
    rmdDict: dict of lists with floats
       Dictionary with lists for Stokes I and V rms noise

    """
    filepathStatistics = "cube." + conf.input.basename + ".statistics.ior-flagged.tab"
    legendList = ["chanNo", "frequency [MHz]",  "rmsStokesI [uJy/beam]", "rmsStokesV [uJy/beam]", "maxStokesI [uJy/beam]", "flagged"]
    info("Writing statistics file: %s", filepathStatistics)
    with open(filepathStatistics, "w") as csvFile:
        writer = csv.writer(csvFile, delimiter="\t")
        csvData = [legendList]
        for i, entry in enumerate(statsDict["rmsStokesI"]):
            chanNo = statsDict['chanNo'][i]
            rmsI = round(statsDict["rmsStokesI"][i], 4)
            rmsV = round(statsDict["rmsStokesV"][i], 4)
            flagged = statsDict['flagged'][i]
            maxI = round(statsDict["maxStokesI"][i], 4)
            freq = round(statsDict["frequency"][i], 4)
            csvData.append([chanNo, freq, rmsI, rmsV, maxI, flagged])
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


# polyom to fit
def h(x, a, b, c):
    x = np.array(x)
    polynom = a*x**2 + b * x + c
    return polynom


def get_yDataFit(xData, a, b, c):
    return h(xData, a, b, c)

def plot_all(statsDict, yDataFit, std, outlierIndexSet, iteration, conf):
    xData = statsDict['chanNo']
    x2Data = statsDict['frequency']
    yData = statsDict['rmsStokesV']
    plt.figure(figsize=(16,8))
    plt.title(r'Iterative outlier rejection, iteration ' + str(iteration))
    plt.xlabel(r'channel',fontsize=22)
    plt.ylabel(r'RMS [µJybeam$^{-1}$]',fontsize=22)

    plt.plot(xData, yData, linestyle='None', marker='.', color='green')
    for i in outlierIndexSet:
        plt.plot(xData[i], yData[i], linestyle='None', marker='.', color='red')


    plt.plot(xData, yDataFit, linestyle='-', marker='', color='blue')

    plt.plot(xData, yDataFit + IOR_LIMIT_SIGMA * std , linestyle='dashed', marker='', color='blue')
    plt.plot(xData, yDataFit - IOR_LIMIT_SIGMA * std , linestyle='dashed', marker='', color='blue')

    # second x-axis on top, which needs to share (twiny) the y-axis
    # TODO: ask Krishna: second x-axis to top
    plt.twiny()
    plt.xlabel(r'frequency [MHz]',fontsize=22)
    plt.tick_params(axis="x")
    plt.plot(x2Data, yData, linestyle='None', marker='None', color='None')

    plt.grid(b=True, which='major', linestyle='dotted')
    plt.minorticks_on()
    sns.despine()
    plt.savefig(conf.env.dirPlots+'diagnostic-outlier-rejection_iteration'+str(iteration)+'.pdf', bbox_inches = 'tight')
    #plt.show()



def get_xyData_after_flagging_by_indexList(indexList, xData, yData):
    xDataNew = []
    yDataNew = []
    for i, asd in enumerate(xData):
        if i not in indexList:
            xDataNew.append(xData[i])
            yDataNew.append(yData[i])
    return [xDataNew, yDataNew]

def get_flaggedIndexList_by_ior_with_fit(xData, yData, outlierIndexSet, xDataInitial, yDataInitial):
    flaggedIndexList = []
    initial_guess_abc = [1, 1, 1]
    xDataCleaned, yDataCleaned = remove_nan_and_zero_from_xyData(xData, yData)
    variables, variables_covariance = optimize.curve_fit(h, xDataCleaned, yDataCleaned, initial_guess_abc)
    a, b, c = variables
    print(variables)
    yDataFit = h(xData, a, b, c)
    yDataFitAllData = h(xDataInitial, a, b, c)
    std = get_std_via_mad(np.array(yDataFit) - np.array(yData))
    for i, asd in enumerate(xDataInitial):
        # above x times sigma
        if yDataInitial[i] > yDataFitAllData[i] + IOR_LIMIT_SIGMA * std:
            flaggedIndexList.append(i)
        # below x times sigma
        elif yDataInitial[i] < yDataFitAllData[i] - IOR_LIMIT_SIGMA * std:
            flaggedIndexList.append(i)
    return [flaggedIndexList, std, [a, b, c]]

def remove_nan_and_zero_from_xyData(xData, yData):
    xDataCleaned = []
    yDataCleaned = []
    for i, y_i in enumerate(yData):
        if np.isnan(y_i) or y_i is 0:
            pass
        else:
            xDataCleaned.append(xData[i])
            yDataCleaned.append(yData[i])
    return [np.array(xDataCleaned), np.array(yDataCleaned)]

def get_flaggedIndexList_for_nan_and_zero(xData, yData):
    flaggedIndexList = []
    for i, asd in enumerate(xData):
        if xData[i] in [0, np.nan] or yData[i] in [0, np.nan]:
            flaggedIndexList.append(i)
    return flaggedIndexList

def get_outlierIndex_and_fitStats_dict(statsDict, conf):
    xData = statsDict['chanNo']
    yData = statsDict['rmsStokesV']
    resultsDict = {}
    resultsDict['xData'] = xData
    resultsDict['yData'] = yData
    xDataInitial = xData
    yDataInitial = yData
    flaggedIndexListOfNanAndZero = get_flaggedIndexList_for_nan_and_zero(xData, yData)
    xData, yData = get_xyData_after_flagging_by_indexList(flaggedIndexListOfNanAndZero, xDataInitial, yDataInitial)
    outlierIndexSet = set(flaggedIndexListOfNanAndZero)
    tmpOutlierIndexList, std, fitCoefficients = get_flaggedIndexList_by_ior_with_fit(xDataInitial, yDataInitial, outlierIndexSet, xDataInitial, yDataInitial)

    outlierSwitch = True
    iteration = 1
    while outlierSwitch:
        outlierIndexLengthBefore = len(outlierIndexSet)
        xData, yData = get_xyData_after_flagging_by_indexList(outlierIndexSet, xDataInitial, yDataInitial)

        tmpOutlierIndexList, std, fitCoefficients = get_flaggedIndexList_by_ior_with_fit(xData, yData, outlierIndexSet, xDataInitial, yDataInitial)

        outlierIndexSet = outlierIndexSet.union(set(tmpOutlierIndexList))
        outlierIndexLengthAfter = len(outlierIndexSet)

        a, b, c = fitCoefficients
        if CREATE_ITERATION_PLOTS:
            plot_all(statsDict, get_yDataFit(resultsDict['xData'], a, b, c), std, outlierIndexSet, iteration, conf)
            iteration += 1
        if outlierIndexLengthBefore == outlierIndexLengthAfter:
            outlierSwitch = False
    resultsDict['outlierIndexSet'] = outlierIndexSet
    resultsDict['sigmaRMS'] = std
    resultsDict['fitCoefficients'] = fitCoefficients
    return resultsDict

def update_flagged_data_in_statsDict(statsDict, outlierIndexSet):
    for i, asd in enumerate(statsDict['flagged']):
        if i in outlierIndexSet:
            statsDict['flagged'][i] = True
    return statsDict

def get_outlierChanNoList_from_outlierIndexSet(statsDict, outlierIndexSet):
    outlierChanNoList = []
    for idx in outlierIndexSet:
        outlierChanNoList.append(statsDict['chanNo'][idx])
    return outlierChanNoList

def flag_chan_in_cube_by_chanNoList(chanNoList, conf):
    """
    Flag channels in data cube.


    """
    cubeName = "cube." + conf.input.basename + ".fits"
    info("Flagging channel Number: {0} in {1}".format(chanNoList, cubeName))
    info(SEPERATOR)
    info("Opening data cube: %s", cubeName)
    # TODO: debug: if ignore_missing_end is not true I get an error.
    hudCube = fits.open(cubeName, memmap=True, ignore_missing_end=True, mode="update")
    dataCube = hudCube[0].data

    info(SEPERATOR)
    for chanNo in chanNoList:
        idx = int(chanNo) - 1
        info(f"Flagging chanNo {chanNo}")
        dataCube[:, idx, :, :] = np.nan
    hudCube.close()

    update_CRPIX3(cubeName)

    info(SEPERATOR)
    info("Generating HDF5 file from: {0}".format(cubeName))
    command = [conf.env.hdf5Converter, cubeName]
    subprocess.run(command)
    info(SEPERATOR)

def get_only_newly_flagged_chanNoList(initialStatsDict, outlierChanNoList):
    '''
    TODO: not optimzed yet. This goes through the whole cube even flagged
    channels are known from the previous statistics
    '''
    chanNoList = []
    for chanNo, flagged in zip(initialStatsDict['chanNo'], initialStatsDict['flagged']):
        if flagged and (chanNo in outlierChanNoList):
            chanNoList.append(chanNo)
    return chanNoList

@main_timer
def main():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    filepathStatistics = "cube." + conf.input.basename + ".statistics.tab"
    statsDict = get_dict_from_tabFile(filepathStatistics)
    initialStatsDict = dict(statsDict)  # make a deep copy
    resultsDict = get_outlierIndex_and_fitStats_dict(statsDict, conf)
    a, b, c = resultsDict['fitCoefficients']
    std = resultsDict['sigmaRMS']
    outlierIndexSet = resultsDict['outlierIndexSet']
    statsDictUpdated = update_flagged_data_in_statsDict(statsDict, outlierIndexSet)
    write_statistics_file(statsDictUpdated, conf)
    outlierChanNoList = get_outlierChanNoList_from_outlierIndexSet(statsDict, outlierIndexSet)

    # optimize: remove channels from list that are already np.nan from cube creation
    outlierChanNoList = get_only_newly_flagged_chanNoList(initialStatsDict, outlierChanNoList)
    flag_chan_in_cube_by_chanNoList(outlierChanNoList, conf)

if __name__ == "__main__":
    CREATE_ITERATION_PLOTS = True
    main()
