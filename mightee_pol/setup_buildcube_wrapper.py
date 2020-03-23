#!python3
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
 environment/container.
-------------------------------------------------------------------------------
'''
import click
import subprocess
import os
from .lhelpers import main_timer, get_config_in_dot_notation
from .setup_buildcube import FILEPATH_CONFIG_TEMPLATE_ORIGINAL


@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
#@main_timer
def main(ctx):
    '''
    '''
    conf = get_config_in_dot_notation(templateFilename=FILEPATH_CONFIG_TEMPLATE_ORIGINAL, configFilename="")
    if "--help" in ctx.args or len(ctx.args) == 0:
        print("TODO: write help")
        return None
    if "--createConfig" in ctx.args:
        subprocess.run(conf.env.commandSingularity.split(" ") + ctx.args)
        ctx.args.remove("--createConfig")
    if "--createScripts" in ctx.args:
        subprocess.run(conf.env.prefixSingularity.split(" ") + conf.env.commandSingularity.split(" ") + ctx.args)
        ctx.args.remove("--createScripts")
    if "--start" in ctx.args:
        subprocess.run(conf.env.commandSingularity.split(" ") + ctx.args)

if __name__=="__main__":
    main()
