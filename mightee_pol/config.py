import os
import mightee_pol

FORMAT_LOGS_TIMESTAMP = "%Y-%m-%d %H:%M:%S,%f"

PATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_JINJA_TEMPLATE = os.path.join(PATH_PACKAGE, "report.template.jinja")

FILEPATH_CONFIG_USER = "meerkat-pol_default_config.txt"

PATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_CONFIG_TEMPLATE = ".meerkat-pol_default_config.template"
FILEPATH_CONFIG_TEMPLATE_ORIGINAL = os.path.join(PATH_PACKAGE, FILEPATH_CONFIG_TEMPLATE)

# TODO: handle this better. Maybe a config.py? Right now this is a checken-egg-problem, therefore hardcoded
FILEPATH_LOG_PIPELINE = "pipeline.log"
FILEPATH_LOG_TIMER = "timer.log"


SPECIAL_FLAGS = [
        "--help",
        "-h",
        "--start",
        "--usage",
        "--createConfig",
        "--createScripts",
        "--readme",
        "--cancel",
        "--kill",
        "--status",
        "-s",
        "--copyScripts",
        ]

