#!/usr/bin/python3

import numpy as np
import logging
import csv
from logging import info, error
from numpy.polynomial.polynomial import polyfit
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib as mpl
from scipy.stats import linregress
from scipy import optimize

from scipy import *

IOR_LIMIT_SIGMA = 4 # n sigma over median

# Outputs a statistics file with estimates for RMS noise in Stokes I and V
FILEPATH_STATISTICS = "cube.statistics.tab"

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

sns.set(font_scale=1.5)
#plt.rcParams.update({'font.size': 12})
mpl.use('Agg') # Backend that doesn't need X server
mpl.rcParams['xtick.labelsize'] = 22
mpl.rcParams['ytick.labelsize'] = 22
mpl.rcParams['axes.titlesize'] = 26
sns.set_style("ticks")
# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

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
    return std


def format_legend(item):
    # remove everything after the first [
    index = item.find('[')
    if index > 0:
        item = item[0:index]
    return item.strip()

def write_statistics_file(statsDict):
    """
    Takes the dictionary with Stokes I and V RMS noise and writes it to a file.

    Parameters
    ----------
    rmdDict: dict of lists with floats
       Dictionary with lists for Stokes I and V rms noise

    """
    statsFilename = FILEPATH_STATISTICS.replace(".tab", ".ior-flagged.tab")
    legendList = ["rmsStokesI [uJy/beam]", "rmsStokesV [uJy/beam]", "flagged", "maxStokesI [uJy/beam]", "frequency [MHz]"]
    info("Writing statistics file: %s", FILEPATH_STATISTICS)
    with open(statsFilename, "w") as csvFile:
        writer = csv.writer(csvFile, delimiter="\t")
        csvData = [legendList]
        for i, entry in enumerate(statsDict["rmsStokesI"]):
            rmsI = round(statsDict["rmsStokesI"][i], 4)
            rmsV = round(statsDict["rmsStokesV"][i], 4)
            #flagged = statsDict['flagged'][i]
            maxI = round(statsDict["maxStokesI"][i], 4)
            freq = round(statsDict["frequency"][i], 4)
            csvData.append([rmsI, rmsV,  maxI, freq])
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

def plot_all(xData, yData, yDataFit, std, outlierIndexSet, iteration):
    plt.figure(figsize=(16,8))
    plt.title(r'RMS vs frequency for COSMOS, iterative outlier rejection, iteration ' + str(iteration))
    plt.xlabel(r'frequency [\,MHz\,]',fontsize=22)
    plt.ylabel(r'RMS [\,µJy\,beam$^{-1}$\,]',fontsize=22)

    plt.plot(xData, yData, linestyle='None', marker='.', color='green')
    for i in outlierIndexSet:
        plt.plot(xData[i], yData[i], linestyle='None', marker='.', color='red')


    plt.plot(xData, yDataFit, linestyle='-', marker='', color='blue')

    plt.plot(xData, yDataFit + IOR_LIMIT_SIGMA * std , linestyle='dashed', marker='', color='blue')

    plt.grid(b=True, which='major', linestyle='dotted')
    plt.minorticks_on()
    sns.despine()
    plt.savefig('RMS-vs-frequency-outlier-rejection_iteration'+str(iteration)+'.pdf', bbox_inches = 'tight')
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
        if yDataInitial[i] > yDataFitAllData[i] + IOR_LIMIT_SIGMA * std:
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

def get_outlierIndex_and_fitStats_dict(xData, yData):
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
            plot_all(resultsDict['xData'], resultsDict['yData'], get_yDataFit(resultsDict['xData'], a, b, c), std, outlierIndexSet, iteration)
            iteration += 1
        if outlierIndexLengthBefore == outlierIndexLengthAfter:
            outlierSwitch = False
    resultsDict['outlierIndexSet'] = outlierIndexSet
    resultsDict['sigmaRMS'] = std
    resultsDict['fitCoefficients'] = fitCoefficients
    return resultsDict

def update_flagged_data_in_statsDict(statsDict, outlierIndexSet):
    #for i, asd in enumerate(statsDict['flagged']):
    #    if i in outlierIndexSet:
    #        statsDict['flagged'][i] = True
    return statsDict

if __name__ == "__main__":
    CREATE_ITERATION_PLOTS = True
    statsDict = get_dict_from_tabFile(FILEPATH_STATISTICS)
    xData = statsDict['frequency']
    yData = statsDict['rmsStokesV']
    resultsDict = get_outlierIndex_and_fitStats_dict(xData, yData)
    a, b, c = resultsDict['fitCoefficients']
    std = resultsDict['sigmaRMS']
    outlierIndexSet = resultsDict['outlierIndexSet']
    statsDictUpdated = update_flagged_data_in_statsDict(statsDict, outlierIndexSet)
    write_statistics_file(statsDictUpdated)
    #plot_all(resultsDict['xData'], resultsDict['yData'], get_yDataFit(resultsDict['xData'], a, b, c), std, outlierIndexSet)
