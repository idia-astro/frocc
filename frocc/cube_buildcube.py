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
import casatasks
from radio_beam import Beam, Beams
from astropy import units

import matplotlib as mpl
mpl.use('Agg') # Backend that doesn't need X server
from matplotlib import pyplot as plt

import numpy as np
from astropy.io import fits

from frocc.lhelpers import get_channelNumber_from_filename, get_config_in_dot_notation, get_std_via_mad, main_timer, change_channelNumber_from_filename,  SEPERATOR, get_lowest_channelNo_with_data_in_cube, update_fits_header_of_cube, DotMap, get_dict_from_click_args
from frocc.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER




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
def smoother(fitsnames, conf):
    """Smooth channel images to common resolution

    Args:
        fitsnames (list): List of fits files to be smoothed
        conf (config): Config object

    Returns:
        list: List of smoothed fits files
    """    
    if conf.input.smoothbeam == "auto":
        beam_list = []
        for fitsname in fitsnames:
            header = fits.getheader(fitsname)
            beam = Beam.from_fits_header(header)
            beam_list.append(beam)
        beams = Beams(
            major=np.array([b.major.to(units.deg).value for b in beam_list])
            * units.deg,
            minor=np.array([b.minor.to(units.deg).value for b in beam_list])
            * units.deg,
            pa=np.array([b.pa.to(units.deg).value for b in beam_list]) * units.deg,
        )
        common_beam = beams.common_beam()
        major = f"{np.ceil(common_beam.major.to(units.arcsec).value)}arcsec"
        minor = f"{np.ceil(common_beam.minor.to(units.arcsec).value)}arcsec"
        pa = f"{np.ceil(common_beam.pa.to(units.deg).value)}deg"
    elif conf.input.smoothbeam.find(",") > 0:
        major, minor = conf.input.smoothbeam.split(",")
        pa = "0deg"
    else:
        major = conf.input.smoothbeam
        minor = conf.input.smoothbeam
        pa = "0deg"
    
    outSmoothedFitsNames = []
    for fitsname in fitsnames:
        outImageName = fitsname.replace(".fits", "")
        outSmoothedName = outImageName + ".smoothed"
        outSmoothedFits = outSmoothedName + ".fits"

        info(f"Importing: {fitsname}")
        casatasks.importfits(
            fitsimage=fitsname, 
            imagename=outImageName,
            overwrite=True,
        )

        casatasks.imsmooth(
            imagename=outImageName,
            outfile=outSmoothedName,
            targetres=True,
            kernel="gauss",
            major=major,
            minor=minor,
            pa=pa,
            overwrite=True,
        )
        info(f"Exporting: {outSmoothedFits}")
        casatasks.exportfits(
            imagename=outSmoothedName, 
            fitsimage=outSmoothedFits, 
            overwrite=True
        )
        outSmoothedFitsNames.append(outSmoothedFits)
    return outSmoothedFitsNames


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
        error("# The frequencies must be expressed in GHz and the angles in radians.")
        error("#fieldname obsid coeffsXY_a coeffsXY_b coeffsXY_c coeffsPol_a coeffsPol_b coeffsPol_c")
        error("XMMLSS12 1538856059 -9.3846e-18  2.3061e-08 -1.3353e+01 -4.6384e-19  1.4007e-09 -1.2145e+00")
        error("XMMLSS12 1539286252  4.3397e-19 -1.1104e-09  3.4366e+00 -1.5629e-18  3.9078e-09 -2.0842e+00")
        error("XMMLSS13 1538942495 -1.1168e-17  2.4598e-08 -1.2223e+01  6.3898e-19 -1.5138e-09  7.4407e-01")
        error("...")


    #df = pd.dfFrame([x.split(' ') for x in result.split('\n')])
    df = df[df['obsid'].astype(str) == str(obsid)]
    return df



def get_and_add_custom_header(lowestChannelFitsfile):
    """
    Gets header from fits file and updates the cube header.


    Parameters
    ----------
    lowestChannelFitsfile: str
       Lowest channel fits filename

    Returns
    -------
    header: astroy.io.fits header
       The header class that was updated

    """
    info(SEPERATOR)

    info("Getting header for data cube from: %s", lowestChannelFitsfile)
    with fits.open(lowestChannelFitsfile, memmap=True) as hud:
        header = hud[0].header
    return header

def get_cropped_size_in_px(conf):
    if type(conf.input.crop) == type("string"):
        width, height = conf.input.crop.strip().split(",")
    else:
        width, height = conf.input.crop
    width_in_px = 0
    height_in_px = 0
    width = str(width)
    height = str(height)
    if width.endswith("px") or width.isdigit():
        width_in_px = int(width.replace("px", ""))
    elif width.endswith("arcsec"):
        width_in_px = int(float(width.replace("arcsec", "")) / float(conf.input.cell))
    elif width.endswith("deg"):
        width_in_px = int(float(width.replace("deg", ""))*3600 / float(conf.input.cell))

    if height.endswith("px") or height.isdigit():
        height_in_px = int(height.replace("px", ""))
    elif height.endswith("arcsec"):
        height_in_px = int(float(height.replace("arcsec", "")) / float(conf.input.cell))
    elif height.endswith("deg"):
        height_in_px = int(float(height.replace("deg", ""))*3600 / float(conf.input.cell))
    return (width_in_px, height_in_px)




def make_empty_image(conf, mode="normal"):
    """
    Generate an empty dummy fits data cube.

    The data cube dimensions are derived from the channel fits images. The
    resulting data cube can exceed the machine's RAM.

    """
    if mode == "smoothed":
        oldChannelFitsfileList = sorted(glob(conf.env.dirImages + "*.chan*image.fits"))
        channelFitsfileList = smoother(oldChannelFitsfileList, conf)
    else:
        channelFitsfileList = sorted(glob(conf.env.dirImages + "*.chan*image.fits"))
        
    lowestChannelFitsfile = channelFitsfileList[0]
    highestChannelFitsfile = channelFitsfileList[-1]
    info(SEPERATOR)
    if conf.input.crop:
        info("Getting image dimension for data cube from flag '--crop %s'", conf.input.crop)
        xdim, ydim = get_cropped_size_in_px(conf)
        with fits.open(lowestChannelFitsfile, memmap=True) as hud:
            xdim_check, ydim_check = np.squeeze(hud[0].data).shape[-2:]
        if xdim_check < xdim or ydim_check < ydim:
            info(f"Input dimensions {xdim_check}px,{ydim_check}px are lower than target '--crop {conf.input.crop}'")
            info(f"Falling back to: {xdim_check}px,{ydim_check}px")
            xdim = xdim_check
            ydim = xdim_check
    else:
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
    header = get_and_add_custom_header(lowestChannelFitsfile)
    for i, dim in enumerate(dims, 1):
        header["NAXIS%d" % i] = dim
        info(header["CRPIX1"])
        info(header["CRPIX2"])
        header["CRPIX1"] = int(xdim/2)
        header["CRPIX2"] = int(ydim/2)
        info(header["CRPIX1"])
        info(header["CRPIX2"])

    if mode == "smoothed":
        cubeName = os.path.join(conf.input.dirOutput, conf.input.basename + conf.env.extCubeSmoothedFits)
    else:
        cubeName = os.path.join(conf.input.dirOutput, conf.input.basename + conf.env.extCubeFits)

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
    return channelFitsfileList



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


def get_cropped_numpy_plane(conf, plane):
    if conf.input.crop:
        plane_height, plane_width = plane.shape
        print(plane_width, plane_height)
        width, height = get_cropped_size_in_px(conf)
        print(width, height)

        if plane_width < width or plane_height < height:
            #info(f"Input dimensions {plane_width}px,{plane_height}px are lower than target '--crop {conf.input.crop}'")
            #info(f"Falling back to: {plane_width}px,{plane_height}px")
            width = plane_width
            height = plane_height

        left = int(plane_width/2 - width/2)
        top = int(plane_height/2 - height/2)
        right = int(plane_width/2 + width/2)
        bottom = int(plane_height/2 + height/2)
        plane = plane[top:bottom, left:right]
        print(plane.shape)
    return plane


def fill_cube_with_images(channelFitsfileList, conf, mode="normal"):
    """
    Fills the empty data cube with fits data.


    """
    if mode == "smoothed":
        cubeName = os.path.join(conf.input.dirOutput, conf.input.basename + conf.env.extCubeSmoothedFits)
    else:
        cubeName = os.path.join(conf.input.dirOutput, conf.input.basename + conf.env.extCubeFits)

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
            stokesV = get_cropped_numpy_plane(conf, hud[0].data[3, 0, :, :])
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
            stokesI = get_cropped_numpy_plane(conf, hud[0].data[0, 0, :, :])
            std = get_std_via_mad(stokesI)
            rmsDict["rmsI"].append(std)
            rmsDict["maxI"].append(np.max(stokesI))
            rmsDict["flagged"].append(False)
            dataCube[0, ii, :, :] = stokesI

            stokesQ = get_cropped_numpy_plane(conf, hud[0].data[1, 0, :, :])
            stokesU = get_cropped_numpy_plane(conf, hud[0].data[2, 0, :, :])
            stokesV = get_cropped_numpy_plane(conf, hud[0].data[3, 0, :, :])

            if conf.input.fileXYphasePolAngleCoeffs:
                info("Starting XY phase and pol angle rotation.")
                # grep obsid from MS filename. TODO: find something better
                basename = os.path.basename(os.path.normpath(conf.input.inputMS[0]))
                obsid = re.search(r"[0-9]{10}", basename)[0]
                info(f"Uning observation ID (obsid): {obsid}")

                coeffs = get_correction_coefficients(conf, obsid)
                info(f"Using correction coefficients: {coeffs.to_dict()}")
                info(f'Image frequency : {rmsDict["freq"][-1]}')

                # correctXYPhase, and convert from GHz to Hz
                coeffsXY = [coeffs['coeffsXY_a'].to_numpy()[0], coeffs['coeffsXY_b'].to_numpy()[0], coeffs['coeffsXY_c'].to_numpy()[0]]
                xyPhaseAngle = second_order_poly(rmsDict["freq"][-1]*1e-9, coeffsXY)
                #xyPhaseAngle = xyPhaseAngle * np.pi/180
                info(f"Using xy-phase angle: {xyPhaseAngle}")
                stokesUtmp = stokesU*np.cos(xyPhaseAngle) - stokesV*np.sin(xyPhaseAngle)
                stokesVtmp = stokesU*np.sin(xyPhaseAngle) + stokesV*np.cos(xyPhaseAngle)

                # correctPolAngle, and convert from GHz to Hz
                coeffsPol = [coeffs['coeffsPol_a'].to_numpy()[0], coeffs['coeffsPol_b'].to_numpy()[0], coeffs['coeffsPol_c'].to_numpy()[0]]
                polAngle = second_order_poly(rmsDict["freq"][-1]*1e-9, coeffsPol)
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

        #if False:
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
        channelFitsfileList = make_empty_image(conf, mode="normal")
        fill_cube_with_images(channelFitsfileList, conf, mode="normal")

    elif int(args.slurmArrayTaskId) == 2:
        channelFitsfileList = make_empty_image(conf, mode="smoothed")
        fill_cube_with_images(channelFitsfileList, conf, mode="smoothed")

    else:
        channelFitsfileList = make_empty_image(conf, mode="normal")
        fill_cube_with_images(channelFitsfileList, conf, mode="normal")



if __name__ == "__main__":
    main()
