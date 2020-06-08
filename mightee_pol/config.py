import os
import mightee_pol

FORMAT_LOGS_TIMESTAMP = "%Y-%m-%d %H:%M:%S,%f"

PATH_PACKAGE = os.path.dirname(mightee_pol.__file__)  # helper
FILEPATH_JINJA_TEMPLATE = os.path.join(PATH_PACKAGE, "report.template.jinja")

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

