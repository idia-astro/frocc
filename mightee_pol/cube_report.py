#!python3
# -*- coding: utf-8 -*-
"""
------------------------------------------------------------------------------


------------------------------------------------------------------------------

 Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
 Inspired by: https://github.com/idia-astro/image-generator
 
 Lennart Heino

------------------------------------------------------------------------------
"""

import requests
import random, string
import os
import re
import sys
import subprocess
import numpy as np
import getpass
from datetime import datetime
from io import StringIO
from jinja2 import Template
from glob import glob
#import seaborn as sns
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
#import seaborn as sns
from astropy.io import fits
import aplpy


from mightee_pol.lhelpers import get_channelNumber_from_filename, get_config_in_dot_notation, get_std_via_mad, main_timer, change_channelNumber_from_filename,  SEPERATOR, get_lowest_channelNo_with_data_in_cube, update_fits_header_of_cube, DotMap, get_dict_from_click_args, calculate_channelFreq_from_header, read_file_as_string, write_file_from_string, get_timestamp, run_command_with_logging, get_dict_from_tabFile, get_lowest_channelIdx_and_freq_with_data_in_cube
from mightee_pol.check_output import print_output
from mightee_pol.config import FORMAT_LOGS_TIMESTAMP, FILEPATH_JINJA_TEMPLATE, FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from mightee_pol.logger import *

#sns.set_style("ticks")
os.environ['LC_ALL'] = "C.UTF-8"
os.environ['LANG'] = "C.UTF-8"


def send_email_via_api(conf, failed=False):
    transferID = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
    email = conf.input.email
    username = getpass.getuser().capitalize()
    if failed:
        subject = f"[ meerkat-pol ] Failed cube {conf.input.basename}"
        oneLineStatus = "the cube creation has failed. You can have  look below and run `meerkat-pol --status` within the working directory to to get a better idea of what went wrong."
    else:
        subject = f"[ meerkat-pol ] New cube {conf.input.basename}"
        oneLineStatus = "the cube creation finished successfully."
    status = get_meerkatpol_check_output(conf)
    body = f'Hi {username},\n\n{oneLineStatus}\n\n```\n{status}\n```\n\nLieben Gruß,\nLennart\'s IDIA API'

    info(f"Sending report to {conf.input.email}")
    apiKey = os.environ.get(conf.env.envVarApikey)
    if apiKey:
        if failed:
            files = []
        else:
            filePath1 = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportPdf)
            filePath2 = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportMD)
            files = [("files", open(filePath1, 'rb')), ("files", open(filePath2, 'rb'))]
        request = requests.post(conf.env.apiUrl, data={"subject": subject, "body":body, "email": email, "transferID": transferID, "apiKey": apiKey}, files=files)
        if str(request).find("[200]") > 0:
            info(f"Connection to {conf.env.apiUrl} sucessfull: {request}")
        else:
            error(f"Connection to {conf.env.apiUrl} failed: {request}")
            error(f"Are you using the right URL and API-key? Please check environment variable {conf.env.envVarApikey}.")
    else:
        error(f"No API key set in environment variable `{conf.env.envVarApikey}`.")
        error(f'Please export API via `export {conf.env.envVarApikey}="API-KEY"`.')
        error(f'You can get a valid API-KEY from Lennart Heino.')


def generate_preview_jpg(conf, mode=None):
    '''
    '''
    if mode == "smoothed":
        filepath = conf.input.basename + conf.env.extCubeAveragemapFits
        savePath = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extCubeAveragemapPreviewJpg)
        data, header = fits.getdata(filepath, header=True)
        title = "Preview: Average map for Stokes I, scalar P, Stokes V"
    else:
        filepath = conf.input.basename + conf.env.extCubeFits
        savePath = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extCubePreviewJpg)
        data, header = fits.getdata(filepath, header=True)
        chanIdxFreqDict = get_lowest_channelIdx_and_freq_with_data_in_cube(filepath)
        title = f"Preview: Cube with Stokes IQUV for channel index {chanIdxFreqDict['chanIdx']} at {round(float(chanIdxFreqDict['freq']),2)} GHz"
#        title = f"Preview: Cube with Stokes IQUV for channel {header['CRPIX3']} at {round(float(header['CRVAL3'])*1e-9,2)} GHz"


    #refChanIdx = int(header['CRPIX3']) - 1
    refChanIdx = get_lowest_channelNo_with_data_in_cube(filepath) - 1
    imgCount = data.shape[0]
    imSize = data.shape[-1]
    if imSize >= 1024:
        downsamplingFactor = imSize//1024
    else:
        downsamplingFactor = 1

    fig = plt.figure(figsize=(imgCount*7, 7))
    fList = []
    #ax = plt.gca()
    fig.suptitle(title, fontsize=imgCount*12, y=1.05+0.006*(imgCount*imgCount))#.set_title(title)
    for ii in range(0, imgCount):
        imgFraction = 1./imgCount
        fList.append(aplpy.FITSFigure(filepath,
            dimensions=(0, 1),
            slices=[refChanIdx, ii],
            figure=fig,
            subplot=[imgFraction*ii, 0, imgFraction, 1],
            downsample=downsamplingFactor),
            )
        fList[ii].show_colorscale(cmap="cubehelix")#, vmin=zmin)
        fList[ii].tick_labels.hide()
        fList[ii].axis_labels.hide()
        fList[ii].ticks.hide()

    info(f"Saving: {savePath}")
    fList[-1].save(savePath, adjust_bbox='tight')

def get_meerkatpol_check_output(conf):
    result = StringIO()
    sys.stdout = result
    print(SEPERATOR)
    print(f"Working directory: {conf.data.workingDirectory}")
    print(f"Slurm jobIDs: {', '.join(list(map(str,conf.data.slurmIDList)))}")
    print_output()
    return result.getvalue()

def write_jinja_reportTemplate(conf):
    #old_stdout = sys.stdout
    status = get_meerkatpol_check_output(conf)
    listobsOutputList = [ read_file_as_string(s) for s in write_listobs_for_inputMS_and_get_filenames(conf) ]
    timestamp = get_timestamp("%H:%M:%S")
    chanStatsDict = get_cube_channel_statsDict(conf)
    iorPlotFilePath = sorted(glob(os.path.join(conf.env.dirPlots, "*pdf")))[-1]
    runtimeDict = get_total_runtime_formated(conf)

    s = read_file_as_string(FILEPATH_JINJA_TEMPLATE)
    tm = Template(s)
    content = tm.render(conf = conf,
            status = status,
            timestamp = timestamp,
            joinpath = os.path.join,
            listobsOutputList = listobsOutputList,
            chanStatsDict = chanStatsDict,
            iorPlotFilePath = iorPlotFilePath,
            runtimeDict = runtimeDict,
            )

    outFile = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportTemplate)
    write_file_from_string(outFile, content)

def create_pdf_from_template(conf):
    fileReportPdfTemplate = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportTemplate)
    fileReportPdf = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportPdf)
    info(f"Generating report pdf...")
    command = f"{conf.env.commandPandoc} {fileReportPdf} {fileReportPdfTemplate}"
    run_command_with_logging(command)

def create_md_from_template(conf):
    filePathReportPdfTemplate = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportTemplate)
    filePathReportMD = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extReportMD)
    info(f"Writing report markdown: {filePathReportMD}")
    templateString = read_file_as_string(filePathReportPdfTemplate)
    #rmove header
    reportMDString = templateString.split('---',2)[-1].strip()
    write_file_from_string(filePathReportMD, reportMDString)
    

def write_listobs_for_inputMS_and_get_filenames(conf):
    filenameList = []
    info(f"Writing `listobs` file via CASA. CASA errors may not be reliable.")
    for inputMS in conf.input.inputMS:
        outFile = os.path.join(conf.env.dirReport, os.path.basename(os.path.splitext(inputMS)[0]) + conf.env.extShortListobs)
        filenameList.append(outFile)
        info(f"Writing file: {outFile}")
        command = f"{conf.env.commandCasa5} \"listobs(vis='{inputMS}', listfile='{outFile}', overwrite=True, verbose=False)\""
        run_command_with_logging(command)
    return filenameList


def get_start_stop_delta_time_from_filepath(filepath):
    contentString = read_file_as_string(filepath)
    # matchString: 2020-05-27 15:07:14,566
    matchString = r'[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}'
    dateList = re.findall(matchString, contentString)
    if dateList:
        start = datetime.strptime(dateList[0], FORMAT_LOGS_TIMESTAMP)
        stop = datetime.strptime(dateList[-1], FORMAT_LOGS_TIMESTAMP)
        delta = stop - start
        return [start, stop, delta]
    else:
        return []


def get_times_listDict(conf):
    dataDict = {}
    dataDict['runScript'] = []
    dataDict['filepath'] = []
    dataDict['timeStart'] = []
    dataDict['timeStop'] = []
    dataDict['timeDelta'] = []
    logFilepathList = glob(os.path.join(conf.env.dirLogs, "*.err"))
    relevantLogFilepathList = []
    for slurmID in conf.data.slurmIDList:
        relevantLogFilepathList += [s for s in logFilepathList if re.search(str(slurmID), s)]
    tmpSort = []
    keyTmpSort = []
    for relevantLogFilepath in relevantLogFilepathList:
        timesList = get_start_stop_delta_time_from_filepath(relevantLogFilepath)
        if timesList:
            tmpSort += [[timesList, relevantLogFilepath]]
            keyTmpSort += [timesList[0]]
    filepathTimesList = [x for _,x in sorted(zip(keyTmpSort, tmpSort))]
    for filepathTimesList in filepathTimesList:
        timesList, filepath = filepathTimesList
        dataDict['filepath'].append(filepath)
        dataDict['timeStart'].append(timesList[0])
        dataDict['timeStop'].append(timesList[1])
        dataDict['timeDelta'].append(timesList[2])
        for runScript in conf.input.runScripts:
            if runScript.replace(".py", "") in filepath:
                dataDict['runScript'].append(runScript)
    return dataDict

def get_total_runtime_formated(conf):
    #dataDict = {}
    dataDict = get_times_listDict(conf)
    totalHours = sum([i.total_seconds() for i in dataDict['timeDelta']])/3600
    humanHours = dataDict['timeStop'][-1] - dataDict['timeStart'][0]
    humanHours = humanHours.total_seconds()/3600
    totalDays = totalHours /24
    humanDays = humanHours /24
    if totalHours > 96:
        totalAuto = str(round(totalHours/24, 1)) + " days"
    else:
        totalAuto = str(round(totalHours, 1)) + " hours"
    if humanHours > 96:
        humanAuto = str(round(humanHours/24, 1)) + " days"
    else:
        humanAuto = str(round(humanHours, 1)) + " hours"

    runtimeDict = dict({'totalAuto': totalAuto, 'humanAuto': humanAuto, 'totalHours': totalHours, 'totalDays': totalDays, 'humanHours': humanHours, 'humanDays': humanDays})
    return runtimeDict


def generate_max_stokesI_plot(conf):
    tabfile = conf.input.basename + conf.env.extCubeIORStatistics
    statsDict = get_dict_from_tabFile(tabfile)
    xData = statsDict['chanNo']
    x2Data = np.array(statsDict['frequency']) /1000  # convert to GHz
    yData = np.array(statsDict['maxStokesI']) / 1e6  # convert to Jy
    fig, ax1 = plt.subplots(figsize=(16,7.5))
    ax1.set_title(r'Stokes I at position of brightest pixel in first valid channel', fontsize=26)
    ax1.set_xlabel(r'channel',fontsize=22)
    ax1.set_ylabel(r'Stokes I max [Jy beam$^{-1}$]',fontsize=22)
    ax1.grid(b=True, which='major', linestyle='dashed')
    ax1.grid(b=True, which='minor', linestyle='dotted')
    ax1.minorticks_on()
    ax1.tick_params(labelsize=22)
    ax1.labelsize = 22

    ax1.plot(xData, yData, linestyle='None', marker='.', color='green', label="Unflagged")
    # only for the label/legend to show the right color
    outlierIndexSet = []
    for jj, flag in enumerate(statsDict['flagged']):
        if flag and yData[jj] != "nan":
            outlierIndexSet.append(jj)
    if outlierIndexSet:
        ax1.plot(xData[list(outlierIndexSet)[0]], yData[list(outlierIndexSet)[0]], linestyle='None', marker='.', color='red', label="Flagged (ior)")
    for i in outlierIndexSet:
        ax1.plot(xData[i], yData[i], linestyle='None', marker='.', color='red')


    ax1.legend(frameon=True, fancybox=True)
    # second x-axis on top, which needs to share (twiny) the y-axis
    # TODO: ask Krishna: second x-axis to top
    ax2 = ax1.twiny()
    ax2.set_xlabel(r'frequency [GHz]',fontsize=22)
    ax2.tick_params(axis="x")
    ax2.tick_params(labelsize=22)
    ax2.plot(x2Data, yData, linestyle='None', marker='None', color='None')

    #PDF
    outFile = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extCubeMaxStokesIPlotPdf)
    fig.savefig(outFile, bbox_inches = 'tight')



def generate_plot_runtimes(conf):
    runtimeDict = get_total_runtime_formated(conf)
    dataDict = get_times_listDict(conf)

    fig, ax1 = plt.subplots(figsize=(8,10))
    ax1.set_title(f'Runtime merkat-pol: On single node {runtimeDict["totalAuto"]}, {runtimeDict["humanAuto"]} wall time')
    ax1.set_xlabel(r'Runtime [hours]')#,fontsize=22)
    ax1.set_ylabel(r'Slurm job count')#,fontsize=22)
    ax1.grid(b=True, which='major', linestyle='dashed')
    ax1.grid(b=True, which='minor', linestyle='dotted')
    ax1.minorticks_on()

    cmap = plt.get_cmap('plasma')
    colors = cmap(np.linspace(0, 1, len(conf.input.runScripts)+1))
    colorIdx = 0
    colorSwitch = dataDict['runScript'][0]
    label = dataDict['runScript'][0]
    for idx, runScript in enumerate(dataDict['runScript']):
        if colorSwitch != runScript:
            colorSwitch = runScript
            label = runScript
            colorIdx += 1
        start = dataDict['timeStart'][idx] - dataDict['timeStart'][0]
        start = start.total_seconds()/3600
        stop = dataDict['timeStop'][idx] - dataDict['timeStart'][0]
        stop = stop.total_seconds()/3600
        plt.plot([start, stop], [idx, idx], linestyle='solid', marker=None, color=colors[colorIdx], label=label, alpha=0.75, linewidth=1)
        label = None
    ax1.legend(frameon=True, fancybox=True)
    outFile = os.path.join(conf.env.dirReport, conf.input.basename + conf.env.extRuntimePdf)
    fig.savefig(outFile, bbox_inches='tight')

def get_cube_channel_statsDict(conf):
    '''
    '''
    dataDict = {}
    dataDict['predicted'] = len([item for sublist in conf.data.predictedOutputChannels for item in sublist])
    tabfile = conf.input.basename + conf.env.extCubeIORStatistics
    statsDict = get_dict_from_tabFile(tabfile)
    dataDict['total'] = len(statsDict['chanNo'])
    iorflaggedCount = 0
    imageCount = 0
    for i, frequency in enumerate(statsDict['frequency']):
        if not np.isnan(frequency) and statsDict['flagged'][i]:
            iorflaggedCount += 1
        if not np.isnan(frequency):
            imageCount += 1
    dataDict['iorflagged'] = iorflaggedCount
    dataDict['imaged'] = imageCount
    dataDict['unflagged'] = imageCount - iorflaggedCount
    dataDict['flagged'] = sum(statsDict['flagged'])
    dataDict['ratio'] = int(round(dataDict['unflagged']/dataDict['total'] *100,0))
    return dataDict


def report_all(conf):
#    try:
    if True:
        generate_max_stokesI_plot(conf)
        generate_plot_runtimes(conf)
        generate_max_stokesI_plot(conf)
        generate_preview_jpg(conf)
        if conf.input.smoothbeam:
            generate_preview_jpg(conf, mode="smoothed")
        write_jinja_reportTemplate(conf)
        create_md_from_template(conf)
        create_pdf_from_template(conf)
        info("Report created.")
        if conf.input.email:
            send_email_via_api(conf)
    #except Exception as e:
    #    error("Report could not be created.")
    #    error(e)
    #    if conf.input.email:
    #        send_email_via_api(conf, failed=True)
#


#@click.command(context_settings=dict(
#    ignore_unknown_options=True,
#    allow_extra_args=True,
#))
##@click.argument('--inputMS', required=False)
#@click.pass_context
@main_timer
def main():
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)
    report_all(conf)



if __name__ == "__main__":
    main()
