#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
-------------------------------------------------------------------------------
 Wrapper script to call setup_buildcube.py within or without a singularity
 container depending on the command line arguments.

 This is necessary because not all packages and programs are accessable from
 all locations on the cluster. For instance, the python CASA6 package can only
 be imported from within the casa6 singularity container and the command
 `sbatch` can only be called from the slurm headnode.

 This script trys to channel the setup_buildcube.py into the correct
 environment/container. This includes the environment variables.
-------------------------------------------------------------------------------
'''
import os
# must come before `import click`
os.environ['LC_ALL'] = "C-UTF-8"
os.environ['LANG'] = "C-UTF-8"

import click
import subprocess
from os.path import expanduser
from mightee_pol.lhelpers import main_timer, get_config_in_dot_notation, print_starting_banner
from mightee_pol.setup_buildcube import FILEPATH_CONFIG_TEMPLATE_ORIGINAL, FILEPATH_LOG_PIPELINE
from mightee_pol.check_input import check_all, print_usage, print_help, print_readme, SPECIAL_FLAGS
from mightee_pol.logger import *


# TODO: put this in default_config.* at a later stage
#PREFIX_SINGULARITY = "srun --qos qos-interactive --nodes=1 --ntasks=1 --time=10 --mem=20GB --partition=Main singularity exec /idia/software/containers/casa-6.simg python3 $HOME/.local/bin/setup_buildcube "
PREFIX_SRUN = "srun --qos qos-interactive -N 1 --preserve-env --mem 40G --ntasks-per-node 8 --cpus-per-task 1 --time 10:00:00 --pty"
#PREFIX_SINGULARITY = "srun --qos qos-interactive -N 1 --mem 20G --ntasks-per-node 1 --cpus-per-task 4 --time 1:00:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg"
#COMMAND = "python3 " + expanduser('~') + "/.local/bin/setup_buildcube"
COMMAND = "setup_buildcube"

PATH_HOME = expanduser("~") + "/"

PATH_QUICKFIX = f"{PATH_HOME}/bin:{PATH_HOME}.local/bin:{PATH_HOME}local/bin:/opt/anaconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:/opt/slurm/bin:/idia/software/pipelines/jordan-dev/processMeerKAT:{PATH_HOME}.local/bin:/idia/software/pipelines/jordan-dev/processMeerKAT/:{PATH_HOME}.fzf/bin:/users/lennart/software"

PYTHONPATH_QUICKFIX = f"{PATH_HOME}.local/lib/python3.7/site-packages/:/idia/software/pipelines/jordan-dev/processMeerKAT:{PATH_HOME}.local/lib/python3.7/site-packages/:/idia/software/pipelines/jordan-dev/processMeerKAT:{PATH_HOME}python-tools:/idia/software/pipelines/jordan-dev/processMeerKAT/:/idia/users/lennart/from-data-scratchtmp/lennart/devel/mightee_pol/"

os.environ['PATH'] = os.environ['PATH'] + ":" + PATH_QUICKFIX
os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + ":" + PYTHONPATH_QUICKFIX


@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
),
    add_help_option=False,
)
#@click.argument('--inputMS', required=False)
@click.pass_context
def main(ctx):
    '''
    '''
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE_ORIGINAL, configFilename="")
    check_all(ctx.args, conf)
    if "--usage" in ctx.args or len(set(SPECIAL_FLAGS).intersection(set(ctx.args))) == 0:
        print_usage()
        return None
    if "--help" in ctx.args or "-h" in ctx.args:
        print_help()
        return None
    if "--readme" in ctx.args:
        print_readme()
        return None
    if "--createConfig" in ctx.args:
        print_starting_banner("MEERKAT-POL --createConfig")
        subprocess.run(conf.env.commandSingularity.replace("${HOME}", PATH_HOME).split(" ") + ctx.args)
        ctx.args.remove("--createConfig")
    if "--createScripts" in ctx.args:
        print_starting_banner("MEERKAT-POL --createScripts")
        commandList = PREFIX_SRUN.split(" ") + conf.env.prefixSingularity.split(" ") + conf.env.commandSingularity.replace("${HOME}", PATH_HOME).split(" ") + ctx.args
        logger.info(f"Command: {' '.join(commandList)}")
        subprocess.run(commandList, env={"SINGULARITYENV_APPEND_PATH": PATH_QUICKFIX, "PATH": PATH_QUICKFIX, "PYTHONPATH": PYTHONPATH_QUICKFIX})
        ctx.args.remove("--createScripts")
    if "--start" in ctx.args:
        print_starting_banner("MEERKAT-POL --start")
        subprocess.run(conf.env.commandSingularity.replace("${HOME}", PATH_HOME).split(" ") + ctx.args)
    if "--cancel" in ctx.args or "--kill" in ctx.args:
        print_starting_banner("MEERKAT-POL --cancel")
        subprocess.run(conf.env.commandSingularity.replace("${HOME}", PATH_HOME).split(" ") + ctx.args)

if __name__=="__main__":
    main()
