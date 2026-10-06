from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from build_stamp import stamp_build_time, TIME_FORMAT


class BuildStampTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='filerenamer build test ')
        self.addCleanup(temp.cleanup)
        self.script = Path(temp.name) / 'version.py'
        self.script.write_text('BUILD_TIME = "2000-01-01_00-00-00"\nprint(BUILD_TIME)\n',
                               encoding='utf-8')

    def test_build_uses_current_host_local_time(self):
        before = datetime.now().replace(microsecond=0)
        timestamp = stamp_build_time(self.script)
        after = datetime.now().replace(microsecond=0)
        recorded = datetime.strptime(timestamp, TIME_FORMAT)
        self.assertLessEqual(before, recorded)
        self.assertLessEqual(recorded, after)
        result = subprocess.run([sys.executable, str(self.script)],
                                check=True, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout, timestamp + '\n')

    def test_rebuild_replaces_timestamp_with_zero_padded_24_hour_time(self):
        for timestamp in ('2026-01-02_00-04-05', '2026-10-05_23-59-58'):
            with self.subTest(timestamp=timestamp):
                stamp_build_time(self.script, timestamp)
                result = subprocess.run([sys.executable, str(self.script)],
                                        check=True, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.stdout, timestamp + '\n')

    def test_malformed_timestamp_does_not_modify_source(self):
        original = self.script.read_bytes()
        for timestamp in ('2026-1-2_3-4-5', '2026-10-05_24-00-00', '2026-02-30_12-00-00'):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    stamp_build_time(self.script, timestamp)
                self.assertEqual(self.script.read_bytes(), original)

    def test_missing_or_duplicate_build_constant_is_rejected(self):
        for content in ('print("no stamp")\n', 'BUILD_TIME = "old"\nBUILD_TIME = "old"\n'):
            with self.subTest(content=content):
                self.script.write_text(content, encoding='utf-8')
                with self.assertRaises(ValueError):
                    stamp_build_time(self.script)
                self.assertEqual(self.script.read_text(encoding='utf-8'), content)


if __name__ == '__main__':
    unittest.main()
