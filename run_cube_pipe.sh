#! /bin/bash

mkdir -p logs vis

IDs=$(sbatch split-observation-from-mms.sbatch | cut -d ' ' -f4)
#ID=$(sbatch split-observation-from-mms.sbatch | cut -d ' ' -f4)
IDs+=,$(sbatch -d afterok:$IDs --kill-on-invalid-dep=yes my-clean-tclean-cube.sbatch | cut -d ' ' -f4)
IDs+=,$(sbatch -d afterok:$IDs --kill-on-invalid-dep=yes generate_huge_fits_cube.sbatch | cut -d ' ' -f4)

echo "Submitted sbatch jobs with following IDS : $IDs"
