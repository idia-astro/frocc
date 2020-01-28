#!python3

import logging
import csv
import numpy as np
import json

from glob import glob
from mightee_pol.lhelpers import get_config_in_dot_notation, main_timer
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from logging import info, error

from RMtools_1D.do_RMsynth_1D import run_rmsynth


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)
SEPERATOR = "-----------------------------------------------------------------"

# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def saveOutput(outdict, arrdict, prefixOut, verbose=True):
    # Save the  dirty FDF, RMSF and weight array to ASCII files
    if verbose: print("Saving the dirty FDF, RMSF weight arrays to ASCII files.")
    outFile = prefixOut + "_FDFdirty.dat"
    if verbose:
        print("> %s" % outFile)
    np.savetxt(outFile, list(zip(arrdict["phiArr_radm2"], arrdict["dirtyFDF"].real, arrdict["dirtyFDF"].imag)))

    outFile = prefixOut + "_RMSF.dat"
    if verbose:
        print("> %s" % outFile)
    np.savetxt(outFile, list(zip(arrdict["phi2Arr_radm2"], arrdict["RMSFArr"].real, arrdict["RMSFArr"].imag)))

    outFile = prefixOut + "_weight.dat"
    if verbose:
        print("> %s" % outFile)
    np.savetxt(outFile, list(zip(arrdict["freqArr_Hz"], arrdict["weightArr"])))

    # Save the measurements to a "key=value" text file
    outFile = prefixOut + "_RMsynth.dat"

    if verbose:
        print("Saving the measurements on the FDF in 'key=val' and JSON formats.")
        print("> %s" % outFile)

    FH = open(outFile, "w")
    for k, v in outdict.items():
        FH.write("%s=%s\n" % (k, v))
    FH.close()


    outFile = prefixOut + "_RMsynth.json"

    if verbose:
        print("> %s" % outFile)
    json.dump(dict(outdict), open(outFile, "w"))


def get_statsList_from_datFile(datFile):
    '''
    TODO: write better
    '''
    allStatsList = [np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([])]
    #allStatsList = [[], [], [], [], [], [], []]
    with open(datFile) as f:
        lines = f.read().splitlines()
        for line in lines:
            # to float
            valueList = [float(i) for i in line.split("\t")]
            for i, item in enumerate(valueList):
                allStatsList[i] = np.append(allStatsList[i], item)
    return allStatsList




@main_timer
def main():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    inputDatList = glob(conf.env.dirRMSYdata + "*tab")

#    statsDict = get_dict_from_tabFile(FILEPATH_STATISTICS)
#    initialStatsDict = dict(statsDict)  # make a deep copy
    allStatsList = get_statsList_from_datFile(inputDatList[0])
    aDict, mDict = run_rmsynth(allStatsList, units="[uJy/beam]", verbose=True, debug=True, showPlots=True)
    saveOutput(aDict, mDict, inputDatList[0].replace(".tab", ""))


if __name__ == "__main__":
    main()
