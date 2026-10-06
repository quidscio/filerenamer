"""Verify the installed console command outside the source checkout."""

from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix='filerenamer installed ') as directory:
        source = Path(directory, 'my file.txt')
        source.write_text('keep this content', encoding='utf-8')
        version = subprocess.run(['filerenamer', '--version'], cwd=directory,
                                 check=True, capture_output=True, text=True, timeout=15)
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\n', version.stdout), version.stdout
        datetime.strptime(version.stdout.strip(), '%Y-%m-%d_%H-%M-%S')
        module_version = subprocess.run([sys.executable, '-m', 'filerenamer', '--version'],
                                        cwd=directory, check=True, capture_output=True,
                                        text=True, timeout=15)
        assert module_version.stdout == version.stdout, 'Entry points disagree on build time'
        assert source.exists(), '--version changed the file'
        preview = subprocess.run(['filerenamer', '--dry-run', '--camelcase', '*.txt'], cwd=directory,
                                 check=True, capture_output=True, text=True, timeout=15)
        assert 'MyFile.txt' in preview.stdout, preview.stdout
        assert source.exists(), 'Preview changed the file'
        cancelled = subprocess.run(['filerenamer', '--camelcase', '*.txt'], cwd=directory,
                                   input='n\n', check=True, capture_output=True, text=True, timeout=15)
        assert '(Y/n)' in cancelled.stdout, cancelled.stdout
        assert source.exists(), 'Declining confirmation changed the file'
        confirmed = subprocess.run(['filerenamer', '--camelcase', '*.txt'], cwd=directory,
                                   input='\n', check=True, capture_output=True, text=True, timeout=15)
        assert '(Y/n)' in confirmed.stdout, confirmed.stdout
        assert Path(directory, 'MyFile.txt').read_text(encoding='utf-8') == 'keep this content'
        assert not source.exists(), 'Original file was not renamed'
    print('Installed CLI smoke test passed.')


if __name__ == '__main__':
    main()
