#!/bin/bash
#SBATCH --array=1-61%30
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=29GB
#SBATCH --job-name=cube_split_and_tclean
#SBATCH --output=logs/cube_split_and_tclean-%A-%a.out
#SBATCH --error=logs/cube_split_and_tclean-%A-%a.err
#SBATCH --partition=Main

cat /etc/hostname

/usr/bin/singularity exec /data/exp_soft/containers/casa-6.simg python cube_split_and_tclean.py --slurmArrayTaskId ${SLURM_ARRAY_TASK_ID}