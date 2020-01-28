#! /bin/bash

IDs=$(sbatch cube_split_and_tclean.sbatch | cut -d ' ' -f4)
#ID=$(sbatch split-observation-from-mms.sbatch | cut -d ' ' -f4)
#IDs+=,$(sbatch -d afterok:$IDs --kill-on-invalid-dep=yes my-clean-tclean-cube.sbatch | cut -d ' ' -f4)
IDs+=,$(sbatch -d afterok:$IDs --kill-on-invalid-dep=yes cube_buildcube.sbatch | cut -d ' ' -f4)

echo "Submitted sbatch jobs with following IDs : $IDs"
