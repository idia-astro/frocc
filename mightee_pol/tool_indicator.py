#!python3
# -*- coding: utf-8 -*-

from mightee_pol.lhelpers import get_std_via_mad, get_config_in_dot_notation, main_timer, update_CRPIX3, SEPERATOR, run_command_with_logging, get_dict_from_tabFile, format_legend
from mightee_pol.config import FILEPATH_CONFIG_TEMPLATE, FILEPATH_CONFIG_USER
from logging import info, error

def message():
    info("This is an indicator message. It helps to track execution times for those scripts that can not utilize the python logger itself. One of these scripts is the HDF5 converter, which gets executed in an sbatch file directly. This also means that the corrosponding log messages appear somewhere else, probably in the *.out file")

@main_timer
def main():
    #conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE, configFilename=FILEPATH_CONFIG_USER)

if __name__ == "__main__":
    main()
