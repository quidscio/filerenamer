"""Embed the build host's local time in the standalone application module."""

from datetime import datetime
from pathlib import Path
import re


TIME_FORMAT = '%Y-%m-%d_%H-%M-%S'


def stamp_build_time(script, timestamp=None):
    timestamp = timestamp or datetime.now().strftime(TIME_FORMAT)
    # Reject malformed overrides before modifying the source file.
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}', timestamp):
        raise ValueError('Build time must use yyyy-mm-dd_hh-mm-ss')
    datetime.strptime(timestamp, TIME_FORMAT)
    script = Path(script)
    source, count = re.subn(r'^BUILD_TIME = "[^"]*"$',
                            f'BUILD_TIME = "{timestamp}"',
                            script.read_text(encoding='utf-8'), flags=re.MULTILINE)
    if count != 1:
        raise ValueError('Expected exactly one BUILD_TIME constant')
    script.write_text(source, encoding='utf-8')
    return timestamp
