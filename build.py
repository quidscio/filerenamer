#!/usr/bin/env python3
"""Cross-platform build: run the test suite, then create an installable wheel."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

from build_stamp import stamp_build_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-build-isolation', action='store_true',
                        help='Use already installed setuptools/wheel (supports offline builds)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    timestamp = stamp_build_time(root / 'filerenamer.py')
    print(f'Build time: {timestamp}', flush=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                   cwd=root, check=True)
    command = [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir',
               str(root / 'dist'), str(root)]
    if args.no_build_isolation:
        command.append('--no-build-isolation')
    subprocess.run(command, cwd=root, check=True,
                   env=dict(os.environ, FILERENAMER_BUILD_TIME=timestamp))
    with ZipFile(root / 'dist' / 'filerenamer-1.0.0-py3-none-any.whl') as wheel:
        packaged_source = wheel.read('filerenamer.py').decode('utf-8')
    if f'BUILD_TIME = "{timestamp}"' not in packaged_source:
        raise RuntimeError('Wheel build time does not match the source build time')
    print(f'Verified wheel build time: {timestamp}')


if __name__ == '__main__':
    main()
