frocc Usage
==================

1. Usage
--------
1. `frocc --createConfig --inputMS <path to input.ms>`
2. `frocc --createScripts`
3. `frocc --start`

2. In one command
-----------------
`frocc --createConfig --inputMS <path to input.ms> --createScripts --start`

3. More advanced
----------------
`frocc --inputMS "/my/data/input1.ms, /my/data/input2.mms" --freqRanges '["900-1000", "1300-1500", "1600-1650"]' --imsize 1024 --niter 500 --threshold 0.0001 --smoothbeam 15arcsec --createConfig --createScripts --start`

5. Canel slurm jobs
-------------------
`frocc --cancel`

5. Further help
---------------
`frocc --readme`
`frocc --help`

frocc Readme
==================

1. Installation
---------------

### Via source:
`source /users/lennart/software/sourcePipeline-stable.sh`

### Via pip (experimental):
1. `git clone git@github.com:idia-astro/frocc.git`
2. `cd frocc`
3. `pip install --user .`

### Via conda:
1. `git clone git@github.com:idia-astro/frocc.git`
2. `cd frocc`
3. `conda env create`

2. Implementation
-----------------

`frocc` takes input measurement set (ms) data and parameters to create
channelized data cube in Stokes IQUV.  
First CASA `split` is run to split out visibilities from the input ms into
visibilities of the aimed resolution in frequency. Then `tclean` runs on each
of these ms separately and creates `.fits`-files for each channel. Next, the
channel files are put into a data cube. The cube is analysed with an iterative
outlier rejection which detects strongly diverging channels by measuring the
RMS in Stokes V by fitting a third order polynomial. Bad channels get flagged
and the cube `.fits`-file is converted into a `.hdf5`-file.  
The aforementioned is realized through the following scripts:
`cube_split.py, cube_tclean.py, cube_buildcube.py, cube_ior_flagging.py`

------------------------------------------------------------------------------

The input of parameters and setting can be controlled via 3 methods:

1. Command line argument: `frocc --inputMS "myData.ms"`
After calling `frocc` with `--createConfig` all settings are written to
`default_config.txt`. (All valid flags can be found in
`.default_config.template` under the `[input]` section).

2. Standard configuration file: `default_config.txt`
After creating `default_config.txt` via `frocc ... ... --createConfig`
it can be revised. All parameters in here overwrite the ones in
`.default_config.template`. Do not change anything under the section `[data]`.

3. Fallback configuration file: `.default_config.template
The pipeline falls back to the values in this file if they have not been
specified via one of the previous way. It is also a place where one can lookup
explanations for valid flags for `frocc`. It also includes the section
`[env]` which can not be controlled via command line flags.

------------------------------------------------------------------------------

When calling `frocc --createScripts` `default_config.txt` and
`.default_config.template` are read and the python and slurm files are copied
to the current directory. The script also tries to calculate the optimal
number of slurm taks depending on the input ms spw coverage.

The last step `frocc --start` submits the slurm files in a dependency
chain. Caution: CASA does not always seem to report back its failure state in
a correct way. Therefore, the slurm flag `--dependency=afterany:...` is
chosen, which starts the next job in the chain even if the previous one has
failed.

### Logging
TODO: It's tricky, CASA's logger gets in the way.


3. Known issues
---------------
- About 2% of cube channels show a differend frequency width


-------------------------------------------------------------------------------
 
  Developed at: IDIA (Institure for Data Intensive Astronomy), Cape Town, ZA
  Inspired by: https://github.com/idia-astro/image-generator
  
  Lennart Heino
 
-------------------------------------------------------------------------------
