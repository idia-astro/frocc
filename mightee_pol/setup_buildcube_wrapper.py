#!python3
'''
Wrapper script to call setup_buildcube.py within or without a singularity
container depending on the command line arguments.
This is necessary because not all packages and programs are accessable from all
locations on the cluster. For instance, the python CASA6 package can only be
imported from within the casa6 singularity container and the command `sbatch`
can only be called from the slurm headnode.
This script trys to channel the setup_buildcube.py into the correct environment.
'''
import click
import subprocess
from .lhelpers import main_timer

# TODO: put this in default_config.* at a later stage
#PREFIX_SINGULARITY = "srun --qos qos-interactive --nodes=1 --ntasks=1 --time=10 --mem=20GB --partition=Main singularity exec /idia/software/containers/casa-6.simg python3 $HOME/.local/bin/setup_buildcube "
PREFIX_SINGULARITY = "srun --qos qos-interactive -N 1 --mem 20G --ntasks-per-node 1 --cpus-per-task 4 --time 1:00:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg"
COMMAND = "python3 /users/lennart/.local/bin/setup_buildcube"

@click.command(context_settings=dict(
    ignore_unknown_options=True,
    allow_extra_args=True,
))
#@click.argument('--inputMS', required=False)
@click.pass_context
@main_timer
def main(ctx):
    '''
    '''
    if "--createConfig" in ctx.args:
        subprocess.run(COMMAND.split(" ") + ctx.args)
        ctx.args.remove("--createConfig")
    if "--createScripts" in ctx.args:
        subprocess.run(PREFIX_SINGULARITY.split(" ") + COMMAND.split(" ") + ctx.args)
        ctx.args.remove("--createScripts")
    if "--start" in ctx.args:
        subprocess.run(COMMAND.split(" ") + ctx.args)

if __name__=="__main__":
    main()
