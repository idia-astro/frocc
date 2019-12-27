#!/bin/bash
#SBATCH --array=1-1%1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=200GB
#SBATCH --job-name=cube_buildcube
#SBATCH --output=logs/cube_buildcube-%A-%a.out
#SBATCH --error=logs/cube_buildcube-%A-%a.err
#SBATCH --partition=Main

cat /etc/hostname

/usr/bin/singularity exec /data/exp_soft/containers/python-3.6.img python3 cube_buildcube.py