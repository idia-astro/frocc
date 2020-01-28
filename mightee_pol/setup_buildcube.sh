#!/bin/bash

# Create files and directories
mkdir -p logs
# Overwirte default_config.txt
cat "" > default_config.txt

srun -N 1 --mem 10G --ntasks-per-node 1 --cpus-per-task 1 --time 10:00:00 --pty singularity exec /data/exp_soft/containers/casa-6.simg python3 setup_buildcube.py --inputMS "test.ms"
