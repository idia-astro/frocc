mightee-pol
===========
Repo to hold all the analysis and cube generation script for MIGHTEE-pol

## Installation
1. git clone https://github.com/idia-astro/mightee-pol
2. 



1. `srun -N 1 --mem 10G --ntasks-per-node 1 --cpus-per-task 1 --time 10:00:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg python ./setup_buildcube.py --createConfig --inputMS "input.ms"` --freqRanges '["890-1600"]'
2. adjust config default_config.txt with settings found in .default_config.template. Don't change .default_config.template, it contains the default fallback values.
3. `srun -N 1 --mem 10G --ntasks-per-node 1 --cpus-per-task 1 --time 10:00:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg python ./setup_buildcube.py --createScripts
4. run cube_split_and_tclean.sbatch and wait for it to finish
5. run cube_buildcube.sbatch
6. run cube_ior_flagging.sbatch

Also via `pip install` installable. Instructions come later since it has some caveats regarding `$PYTHONPATH` in a singularity container.

TODO
====
- optimisations 
- more statistics
- cleanup
