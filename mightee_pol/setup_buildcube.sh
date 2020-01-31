#!/bin/bash
# short helper script to run setup_buildcube.py in a 
srun -N 1 --mem 20G --ntasks-per-node 1 --cpus-per-task 1 --time 00:20:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg python3 setup_buildcube.py $@
