"""Stamp package builds, including direct pip install/wheel builds."""

import os
from pathlib import Path
import sys

from setuptools import setup
from setuptools.command.build_py import build_py

# PEP 517 frontends do not necessarily include the source directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_stamp import stamp_build_time


class StampedBuildPy(build_py):
    def run(self):
        super().run()
        stamp_build_time(Path(self.build_lib) / 'filerenamer.py',
                         os.environ.get('FILERENAMER_BUILD_TIME'))


setup(cmdclass={'build_py': StampedBuildPy})
