#!/bin/bash
#SBATCH --array=1-1%1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2GB
#SBATCH --job-name=cube_ior_flagging
#SBATCH --output=logs/cube_ior_flagging-%A-%a.out
#SBATCH --error=logs/cube_ior_flagging-%A-%a.err
#SBATCH --partition=Main

cat /etc/hostname

/usr/bin/singularity exec /data/exp_soft/containers/python-3.6.img python3 cube_ior_flagging.py