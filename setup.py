#!/usr/bin/env python3
import setuptools
import sys

# not working
sys.executable = "/usr/bin/env python3"

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="frocc",  # Replace with your own username
    version="0.0.1",
    author="Lennart Heino",
    author_email="author@example.com",
    description="Fast RadiO Cube Creation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/idia-astro/frocc",
    include_package_data=True,
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            "forcc = frocc.setup_buildcube_wrapper:main",
            "setup_buildcube = frocc.setup_buildcube:main",
#            "setup_buildcube = setup_buildcube.sh",
        ],
    },
    # not working
    options = {
        'build_scripts': {
            'executable': "/usr/bin/env python3",
        },
    },


)
