#! /bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --mem 200GB
#SBATCH --job-name=bc
#SBATCH --output=logs/buildcube-%A_%a.out
#SBATCH --error=logs/buildcube-%A_%a.err
#SBATCH --partition=Main
#SBATCH --account=b05-pipelines-ag


/usr/bin/singularity exec /data/exp_soft/containers/python-3.6.img python3 cube_buildcube.py
