'''
Still in development
Make sure all of the slurm commands get catched.
'''
#from mightee_pol.setup_buildcube import FILEPATH_LOG_PIPELINE
import logging

# TODO, hardcoded because of dependecy circle. Fix this
FILEPATH_LOG_PIPELINE = "pipeline.log"

logger = logging.getLogger('general')
logger.setLevel(logging.INFO)
fh = logging.FileHandler(FILEPATH_LOG_PIPELINE)
fh.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s\t[ %(levelname)s ]\t%(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

info = logger.info
debug = logger.debug
warning = logger.warning
error = logger.error



