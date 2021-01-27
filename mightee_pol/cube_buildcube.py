#!python3
# -*- coding: utf-8 -*-
"""
------------------------------------------------------------------------------

 This script generates an empty dummy 4 dimensional data cube in fits format.
 After the initialisation this cube gets filled with fits image data. The
 cube header gets updated from the first image in `env.dirImages`.
 This script can be used to generate fits data cubes of sizes that exceeds the
 machine's RAM (tested with 234 GB RAM and 335 GB cube data).

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
import click
import pandas as pd
import seaborn as sns

import matplotlib as mpl
mpl.use('Agg') # Backend that doesn't need X server
from matplotlib import pyplot as plt

import numpy as np
from astropy.io import fits

from mightee_pol.lhelpers import get_channelNumber_from_filename, get_config_in_dot_notation, get_std_via_mad, main_timer, change_channelNumber_from_filename,  SEPERATOR, get_lowest_channelNo_with_data_in_cube, update_fits_header_of_cube, DotMap, get_dict_from_click_args
from mightee_pol.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER




# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# SETTINGS

logging.basicConfig(
    format="%(asctime)s\t[ %(levelname)s ]\t%(message)s", level=logging.INFO
)

mpl.rcParams['xtick.labelsize'] = 22
mpl.rcParams['ytick.labelsize'] = 22
mpl.rcParams['axes.titlesize'] = 26
sns.set_style("ticks")
# SETTINGS
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def second_order_poly(x, coeffs):
    #y = a*x**2 + b*x + c
    poly = np.poly1d(coeffs)
    y = poly(x)
    return y

def get_correction_coefficients(conf, obsid):
    try:
        info(f"Reading coefficient file with rotation parameters: {conf.input.fileXYphasePolAngleCoeffs}")
        df = pd.read_csv(conf.input.fileXYphasePolAngleCoeffs, header=3, delim_whitespace=True)
    except Exception as e:
        error(e)
        error(f"Problem reading {conf.input.fileXYphasePolAngleCoeffs}. Is the file in the correct format? Similar to:")
        error("")
        error("# CoeffsXY and coeffsPol are second order polynomials of the form y = ax^2 + bx + c")
        error("# The XY phases must be rotated first prior to rotating the polarization angle.")
        error("# The frequencies must be expressed in Hz and the angles in radians.")
        error("#fieldname obsid coeffsXY_a coeffsXY_b coeffsXY_c coeffsPol_a coeffsPol_b coeffsPol_c")
        error("XMMLSS12 1538856059 -9.3846e-18  2.3061e-08 -1.3353e+01 -4.6384e-19  1.4007e-09 -1.2145e+00")
        error("XMMLSS12 1539286252  4.3397e-19 -1.1104e-09  3.4366e+00 -1.5629e-18  3.9078e-09 -2.0842e+00")
        error("XMMLSS13 1538942495 -1.1168e-17  2.4598e-08 -1.2223e+01  6.3898e-19 -1.5138e-09  7.4407e-01")
        error("...")


    #df = pd.dfFrame([x.split(' ') for x in result.split('\n')])
    df = df[df['obsid'].astype(str) == str(obsid)]
    return df



def get_and_add_custom_header(header, zdim, conf, mode="normal"):
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
    if mode == "smoothed":
        lowestChannelFitsfile = sorted(glob(conf.env.dirImages + "*image.smoothed.fits"))[0]
    else:
        lowestChannelFitsfile = sorted(glob(conf.env.dirImages + "*image.fits"))[0]

    info("Getting header for data cube from: %s", lowestChannelFitsfile)
    with fits.open(lowestChannelFitsfile, memmap=True) as hud:
        header = hud[0].header
    #    # Optional: Update the header.
    #    header["OBJECT"] = str(conf.data.field)
    #    header["NAXIS3"] = int(zdim)
    #    header["CTYPE3"] = ("FREQ", "")
    return header


def make_empty_image(conf, mode="normal"):
    """
    Generate an empty dummy fits data cube.

    The data cube dimensions are derived from the channel fits images. The
    resulting data cube can exceed the machine's RAM.

    """
    if mode == "smoothed":
        channelFitsfileList = sorted(glob(conf.env.dirImages + "*image.smoothed.fits"))
    else:
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
    info(f"Z-dimension: {zdim}")

    info("Assuming full Stokes for dimension W.")
    wdim = 4
    info("W-dimension: %s", wdim)

    dims = tuple([xdim, ydim, zdim, wdim])

    # create header

    dummy_dims = tuple(1 for d in dims)
    #dummy_data = np.ones(dummy_dims, dtype=np.float64) * np.nan
    #dummy_data = dummy_data.fill(np.nan)
    dummy_data = np.zeros(dummy_dims, dtype=np.float32)
    hdu = fits.PrimaryHDU(data=dummy_data)

    header = hdu.header
    header = get_and_add_custom_header(header, zdim, conf, mode=mode)
    for i, dim in enumerate(dims, 1):
        header["NAXIS%d" % i] = dim

    if mode == "smoothed":
        cubeName = conf.input.basename + conf.env.extCubeSmoothedFits
    else:
        cubeName = conf.input.basename + conf.env.extCubeFits

    header.tofile(cubeName, overwrite=True)

    # create full-sized zero image

    header_size = len(
        header.tostring()
    )  # Probably 2880. We don't pad the header any more; it's just the bare minimum
    data_size = np.product(dims) * np.dtype(np.float32).itemsize
    # This is not documented in the example, but appears to be Astropy's default behaviour
    # Pad the total file size to a multiple of the header block size
    block_size = 2880
    data_size = block_size * (((data_size -1) // block_size) + 1)

    with open(cubeName, "rb+") as f:
        f.seek(header_size + data_size - 1)
        f.write(b"\0")



def check_rms(npArray):
    """
    Check if the Numpy Array is above 1e-6 uJy/beam.

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
    if (std < 1e-6):
        npArray = np.nan
        std = np.nan
    return [npArray, std]


def write_statistics_file(statsDict, conf, mode="normal"):
    """
    Takes the dictionary with Stokes I and V RMS noise and writes it to a file.

    Parameters
    ----------
    rmdDict: dict of lists with floats
       Dictionary with lists for Stokes I and V rms noise

    """
    # Outputs a statistics file with estimates for RMS noise in Stokes I and V
    if mode == "smoothed":
        filepathStatistics = conf.input.basename + conf.env.extCubeSmoothedStatistics
    else:
        filepathStatistics = conf.input.basename + conf.env.extCubeStatistics
    legendList = ["chanNo", "frequency [MHz]", "rmsStokesI [uJy/beam]", "rmsStokesV [uJy/beam]",  "maxStokesI [uJy/beam]", "flagged", "xyPhaseCorr", "polAngleCorr"]
    info("Writing statistics file: %s", filepathStatistics)
    with open(filepathStatistics, "w") as csvFile:
        writer = csv.writer(csvFile, delimiter="\t")
        csvData = [legendList]
        for ii, entry in enumerate(statsDict["rmsI"]):
            chanNo = statsDict["chanNo"][ii]
            freq = round(statsDict["freq"][ii] * 1e-6, 4)
            rmsI = round(statsDict["rmsI"][ii] * 1e6, 4)
            rmsV = round(statsDict["rmsV"][ii] * 1e6, 4)
            maxI = round(statsDict["maxI"][ii] * 1e6, 4)
            xyPhaseCorr = round(statsDict["xyPhaseCorr"][ii], 4)
            polAngleCorr = round(statsDict["polAngleCorr"][ii], 4)
            flagged = statsDict["flagged"][ii]
            csvData.append([chanNo, freq, rmsI, rmsV, maxI, flagged, xyPhaseCorr, polAngleCorr])
        writer.writerows(csvData)

def plot_xyPhaseCorr_and_polAngleCorr(statsDict,  conf):
    xData = statsDict['freq']
    yData = statsDict['xyPhaseCorr']
    y2Data = statsDict['polAngleCorr']
    fig, ax1 = plt.subplots(figsize=(16,7.5))
    ax1.set_title(r'xy-phase and polarization angle correction')
    ax1.set_xlabel(r'frequency [Hz]',fontsize=22)
    ax1.set_ylabel(r'angle [rad]',fontsize=22)
    ax1.grid(b=True, which='major', linestyle='dashed')
    ax1.grid(b=True, which='minor', linestyle='dotted')
    ax1.minorticks_on()

    ax1.plot(xData, yData, linestyle='-', marker='.', color='green', label="xy-phase correction")
    ax1.plot(xData, y2Data, linestyle='-', marker='.', color='blue', label="pol. angle correction")

    ax1.legend(frameon=True, fancybox=True)

    #PDF
    plotPath = conf.env.dirPlots+conf.input.basename+'.diagnostic-xyPhaseCorr-polAngleCorr.pdf'
    info(f"Saving plot: {plotPath}")
    fig.savefig(plotPath, bbox_inches = 'tight')
    # PNG
    plotPath = conf.env.dirPlots+conf.input.basename+'.diagnostic-xyPhaseCorr-polAngleCorr.png'
    info(f"Saving plot: {plotPath}")
    fig.savefig(plotPath, bbox_inches = 'tight')
    #plt.show()


def fill_cube_with_images(conf, mode="normal"):
    """
    Fills the empty data cube with fits data.


    """
    if mode == "smoothed":
        cubeName = conf.input.basename + conf.env.extCubeSmoothedFits
    else:
        cubeName = conf.input.basename + conf.env.extCubeFits
    info(SEPERATOR)
    info(f"Opening data cube: {cubeName}")
    # TODO: debug: if ignore_missing_end is not true I get an error.
    hudCube = fits.open(cubeName, memmap=True, ignore_missing_end=True, mode="update")
    dataCube = hudCube[0].data
    highestChannel = int(dataCube.shape[1] + 1)

    rmsDict = {}
    rmsDict["chanNo"] = []
    rmsDict["freq"] = []
    rmsDict["rmsI"] = []
    rmsDict["rmsV"] = []
    rmsDict["maxI"] = []
    rmsDict["flagged"] = []
    rmsDict["polAngleCorr"] = []
    rmsDict["xyPhaseCorr"] = []
    if mode == "smoothed":
        channelFitsfileList = sorted(glob(conf.env.dirImages + "*image.smoothed.fits"))
    else:
        channelFitsfileList = sorted(glob(conf.env.dirImages + "*image.fits"))
    maxChanNo =  int(get_channelNumber_from_filename(channelFitsfileList[-1], conf.env.markerChannel))
    for ii in range(0, maxChanNo):
        rmsDict['chanNo'].append(ii + 1)
        hudSwitch = False
        channelFitsfile = change_channelNumber_from_filename(channelFitsfileList[0], conf.env.markerChannel, ii + 1)
        info(f"Trying to open fits file: {channelFitsfile}")
        # Switch
        stokesVflag = False

        # Try to open file. If channel doesn't exists flag channel
        try:
            hud = fits.open(channelFitsfile, memmap=True)
            rmsDict['freq'].append(hud[0].header["CRVAL3"])
            stokesV = hud[0].data[3, 0, :, :]
            checkedArray, std = check_rms(stokesV)
            rmsDict["rmsV"].append(std)
            dataCube[3, ii, :, :] = checkedArray
            if np.isnan(np.sum(checkedArray)) or std==0:
                stokesVflag = True
                rmsDict['freq'][-1] = np.nan
            hudSwitch = True
        except:
            info(f"Flagging channel, can not open file: {channelFitsfile}")
            stokesVflag = True
            rmsDict["freq"].append(np.nan)
            rmsDict["rmsV"].append(np.nan)

        if not stokesVflag:
            stokesI = hud[0].data[0, 0, :, :]
            std = get_std_via_mad(stokesI)
            rmsDict["rmsI"].append(std)
            rmsDict["maxI"].append(np.max(stokesI))
            rmsDict["flagged"].append(False)
            dataCube[0, ii, :, :] = stokesI

            stokesQ = hud[0].data[1, 0, :, :]
            stokesU = hud[0].data[2, 0, :, :]
            stokesV = hud[0].data[3, 0, :, :]

            if conf.input.fileXYphasePolAngleCoeffs:
                info("Starting XY phase and pol angle rotation.")
                # grep obsid from MS filename. TODO: find something better
                basename = os.path.basename(os.path.normpath(conf.input.inputMS[0]))
                obsid = re.search(r"[0-9]{10}", basename)[0]
                info(f"Uning observation ID (obsid): {obsid}")

                coeffs = get_correction_coefficients(conf, obsid)
                info(f"Using correction coefficients: {coeffs.to_dict()}")
                info(f'Image frequency : {rmsDict["freq"][-1]}')

                # correctXYPhase
                coeffsXY = [coeffs['coeffsXY_a'].to_numpy()[0], coeffs['coeffsXY_b'].to_numpy()[0], coeffs['coeffsXY_c'].to_numpy()[0]]
                xyPhaseAngle = second_order_poly(rmsDict["freq"][-1], coeffsXY)
                #xyPhaseAngle = xyPhaseAngle * np.pi/180
                info(f"Using xy-phase angle: {xyPhaseAngle}")
                stokesUtmp = stokesU*np.cos(xyPhaseAngle) - stokesV*np.sin(xyPhaseAngle)
                stokesVtmp = stokesU*np.sin(xyPhaseAngle) + stokesV*np.cos(xyPhaseAngle)

                # correctPolAngle
                coeffsPol = [coeffs['coeffsPol_a'].to_numpy()[0], coeffs['coeffsPol_b'].to_numpy()[0], coeffs['coeffsPol_c'].to_numpy()[0]]
                polAngle = second_order_poly(rmsDict["freq"][-1], coeffsPol)
                #polAngle = polAngle * np.pi/180
                info(f"Using polarization angle: {polAngle}")
                stokesQtmp = stokesQ*np.cos(polAngle) - stokesUtmp*np.sin(polAngle)
                stokesUtmp = stokesQ*np.sin(polAngle) + stokesUtmp*np.cos(polAngle)
                stokesQ = stokesQtmp
                stokesU = stokesUtmp
                stokesV = stokesVtmp
                rmsDict["xyPhaseCorr"].append(xyPhaseAngle)
                rmsDict["polAngleCorr"].append(polAngle)

            elif not conf.input.fileXYphasePolAngleCoeffs:
                rmsDict["xyPhaseCorr"].append(np.nan)
                rmsDict["polAngleCorr"].append(np.nan)

            dataCube[1, ii, :, :] = stokesQ
            dataCube[2, ii, :, :] = stokesU
            dataCube[3, ii, :, :] = stokesV

        elif stokesVflag:
            dataCube[:, ii, :, :] = np.nan
            rmsDict["rmsI"].append(np.nan)
            rmsDict["maxI"].append(np.nan)
            rmsDict["flagged"].append(True)
            rmsDict["xyPhaseCorr"].append(np.nan)
            rmsDict["polAngleCorr"].append(np.nan)
            info(
                "Stokes V RMS noise of {0} is below below 1 [uJy/beam]. Flagging Stokes IQUV.".format(round(rmsDict["rmsV"][-1] * 1e6, 2))
            )

        if hudSwitch:
            hud.close()
    info(SEPERATOR)


    hudCube.close()
    # TODO, check whether lowestChanNo is necessary
    # lowestChanNo = get_lowest_channelNo_with_data_in_cube(cubeName)
    addFitsHeaderDict = {
            "CRPIX3": 1, #lowestChanNo,
            "OBJECT": str(conf.data.field),
            "NAXIS3": highestChannel,
            "CTYPE3": ("FREQ", ""),
            "COMMENT": "Created by IDIA Pipeline"
            }
    update_fits_header_of_cube(cubeName, addFitsHeaderDict)
    write_statistics_file(rmsDict, conf, mode=mode)
    if conf.input.fileXYphasePolAngleCoeffs:
        plot_xyPhaseCorr_and_polAngleCorr(rmsDict, conf)

def move_casalogs_to_dirLogs(conf):
    '''
    casataks.casalog.setcasalog doesn't seem to work. It instead puts alls casa
    logs into the working directory. This is just a dirty fix to put the logs
    in conf.env.dirLogs
    '''
    try:
        info(f"Moving casa log files from working directory to {conf.env.dirLogs}")
        casalogList = glob("casa*.log")
        for casalog in casalogList:
            os.replace(casalog, os.path.join(conf.env.dirLogs, casalog))
    except:
        pass


@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx):
    args = DotMap(get_dict_from_click_args(ctx.args))
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    info(f"Scripts config: {conf}")
    move_casalogs_to_dirLogs(conf)

    # exploit slurm task ID to run normal buildcube or smoothed buildcube
    if int(args.slurmArrayTaskId) == 1:
        make_empty_image(conf, mode="normal")
        fill_cube_with_images(conf, mode="normal")

    elif int(args.slurmArrayTaskId) == 2:
        make_empty_image(conf, mode="smoothed")
        fill_cube_with_images(conf, mode="smoothed")

    else:
        make_empty_image(conf, mode="normal")
        fill_cube_with_images(conf, mode="normal")



if __name__ == "__main__":
    main()
