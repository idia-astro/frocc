#!/bin/bash
#SBATCH --array 70-90%20
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=20GB
#SBATCH --job-name=cstclean
#SBATCH --output=logs/cube_split_and_tclean-%A-%a.out
#SBATCH --error=logs/cube_split_and_tclean-%A-%a.err
#SBATCH --partition Main

cat /etc/hostname

/usr/bin/singularity exec /data/exp_soft/containers/casameer-5.5.0-149-bdsf.simg "casa" --nogui --nologger --logfile logs/cube_split_and_tclean-${SLURM_ARRAY_JOB_ID}-${SLURM_ARRAY_TASK_ID}.casa -c cube_split_and_tclean.py --slurmJobId ${SLURM_ARRAY_TASK_ID}
