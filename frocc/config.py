import os
import frocc


FORMAT_LOGS_TIMESTAMP = "%Y-%m-%d %H:%M:%S,%f"

PATH_PACKAGE = list(frocc.__path__)[0]  # helper
FILEPATH_JINJA_TEMPLATE = os.path.join(PATH_PACKAGE, "report.template.jinja")

FILEPATH_CONFIG_USER = "frocc_default_config.txt"

FILEPATH_CONFIG_TEMPLATE = ".frocc_default_config.template"
FILEPATH_CONFIG_TEMPLATE_ORIGINAL = os.path.join(PATH_PACKAGE, FILEPATH_CONFIG_TEMPLATE)

# TODO: handle this better. Maybe a config.py? Right now this is a checken-egg-problem, therefore hardcoded
FILEPATH_LOG_PIPELINE = "pipeline.log"
FILEPATH_LOG_TIMER = "timer.log"


SPECIAL_FLAGS = [
        "--help",
        "--help-verbose",
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

