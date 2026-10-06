import contextlib
from datetime import datetime
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import filerenamer


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'filerenamer.py'


class NamingTests(unittest.TestCase):
    def test_default_replacements(self):
        examples = {
            'my file.txt': 'my-file.txt',
            'a：b，c.txt': 'a_b-c.txt',
            'a  --b__::c.txt': 'a-b_c.txt',
            'a“b”‘c’d\'e.txt': 'a_b_c_d_e.txt',
            'safe-name_file.tar.gz': 'safe-name_file.tar.gz',
            'café 東京.txt': 'café-東京.txt',
        }
        for original, expected in examples.items():
            with self.subTest(original=original):
                self.assertEqual(filerenamer.sanitize_filename(original), expected)

    def test_camelcase_names(self):
        examples = {
            'my file: name.txt': 'MyFileName.txt',
            'my-file_name.txt': 'MyFileName.txt',
            '  my---file___name  .txt': 'MyFileName.txt',
            'my file': 'MyFile',
            'my file.tar.gz': 'MyFile.tar.gz',
            'my file.TXT': 'MyFile.TXT',
            'my file.t? x_t': 'MyFile.txt',
            'my file.tar?.g z': 'MyFile.tar.gz',
            'myFile.txt': 'MyFile.txt',
            'HTTP server.txt': 'HTTPServer.txt',
            'alreadyCamelCase.txt': 'AlreadyCamelCase.txt',
            'café 東京.txt': 'Café東京.txt',
            'cafe\u0301 noir.txt': 'Cafe\u0301Noir.txt',
            'my\u00a0file\u3000name.txt': 'MyFileName.txt',
            'my\tfile\nname.txt': 'MyFileName.txt',
            'my［file］（name）.txt': 'MyFileName.txt',
            '.my config': '.MyConfig',
            '.my config.json': '.MyConfig.json',
            'my file... ': 'MyFile',
            '???---__ .txt': 'File.txt',
            '   ': 'File',
        }
        for original, expected in examples.items():
            with self.subTest(original=original):
                result = filerenamer.sanitize_filename(original, camelcase=True)
                self.assertEqual(result, expected)
                self.assertEqual(filerenamer.sanitize_filename(result, camelcase=True), result)

    def test_every_windows_forbidden_character(self):
        for character in '<>:"/\\|?*' + ''.join(chr(n) for n in range(32)):
            with self.subTest(character=repr(character)):
                original = 'my' + character + 'file.txt'
                self.assertEqual(filerenamer.sanitize_filename(original, True), 'MyFile.txt')
                self.assertNotIn(character, filerenamer.sanitize_filename(original))

    def test_all_legacy_mappings_are_word_boundaries_in_camelcase(self):
        for character in filerenamer.CHAR_MAP:
            with self.subTest(character=character):
                self.assertEqual(filerenamer.sanitize_filename('my' + character + 'file', True),
                                 'MyFile')

    def test_windows_device_names_and_trailing_dots(self):
        for name in filerenamer.WINDOWS_RESERVED_NAMES:
            for extension in ('', '.txt', '.tar.gz'):
                with self.subTest(name=name, extension=extension):
                    self.assertEqual(filerenamer.sanitize_filename(name + extension, True),
                                     name + 'File' + extension)
                    self.assertEqual(filerenamer.sanitize_filename(name + extension),
                                     '_' + name + extension)
        self.assertEqual(filerenamer.sanitize_filename('con.txt', True), 'ConFile.txt')
        self.assertEqual(filerenamer.sanitize_filename('name...'), 'name')
        self.assertEqual(filerenamer.sanitize_filename('...'), 'File')
        self.assertEqual(filerenamer.sanitize_filename('COM10.txt', True), 'COM10.txt')


class FilesystemTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='filerenamer tests ')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def create(self, name, contents='original contents'):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding='utf-8')
        return path

    def run_cli(self, *args, expected=0, response=''):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.directory,
                                input=response, capture_output=True, text=True, encoding='utf-8',
                                env=env, timeout=15)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def assert_file(self, name, contents='original contents'):
        self.assertEqual((self.directory / name).read_text(encoding='utf-8'), contents)


class CliTests(FilesystemTestCase):
    def test_version_prints_only_the_build_time_and_never_renames(self):
        self.create('my file.txt')
        for arguments in (('--version',), ('-w', '--camelcase', '--version', 'my file.txt'),
                          ('--version', 'missing file.txt')):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments, response='\n')
                self.assertEqual(result.stdout, filerenamer.BUILD_TIME + '\n')
                self.assertEqual(result.stderr, '')
                self.assertRegex(result.stdout, r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\n$')
                datetime.strptime(result.stdout.strip(), '%Y-%m-%d_%H-%M-%S')
                self.assert_file('my file.txt')
                self.assertFalse((self.directory / 'MyFile.txt').exists())

    def test_help_exits_successfully_without_renaming(self):
        self.create('my file.txt')
        for flag in ('-h', '--help'):
            with self.subTest(flag=flag):
                result = self.run_cli(flag)
                for text in ('--camelcase', '--wet', '--dry-run', '--recursive', '--quiet', '--version', 'PATH',
                             '"*.txt"', '**/*.txt', 'CMD', 'preview', 'exit status', '(Y/n)',
                             'Enter, y, or Y', 'Any other input cancels'):
                    self.assertIn(text, result.stdout)
                self.assert_file('my file.txt')

    def test_default_directory_proposes_then_cancels_with_closed_stdin(self):
        self.create('my file.txt')
        result = self.run_cli()
        self.assertIn('my-file.txt', result.stdout)
        self.assertIn('1 files would be renamed', result.stdout)
        self.assertIn('(Y/n)', result.stdout)
        self.assertIn('Cancelled', result.stdout)
        self.assert_file('my file.txt')
        self.assertFalse((self.directory / 'my-file.txt').exists())

    def test_default_flow_accepts_only_enter_y_or_uppercase_y(self):
        for response in ('\n', 'y\n', 'Y\n'):
            for flags, target in (([], 'my-file.txt'), (['--camelcase'], 'MyFile.txt')):
                with self.subTest(response=repr(response), flags=flags):
                    self.create('my file.txt')
                    result = self.run_cli(*flags, 'my file.txt', response=response)
                    self.assertIn(f'my file.txt -> {target}', result.stdout)
                    self.assertEqual(result.stdout.count('(Y/n)'), 1)
                    self.assertLess(result.stdout.index('Proposed:'), result.stdout.index('(Y/n)'))
                    self.assertLess(result.stdout.index('(Y/n)'), result.stdout.index('Renaming:'))
                    self.assert_file(target)
                    self.assertFalse((self.directory / 'my file.txt').exists())
                    (self.directory / target).unlink()

    def test_other_responses_cancel_without_reprompting(self):
        self.create('my file.txt')
        for response in ('n\n', 'N\n', 'no\n', 'yes\n', 'YES\n', 'other\n',
                         ' \n', ' y\n', 'y \n', 'n\ny\n', ''):
            with self.subTest(response=repr(response)):
                result = self.run_cli('my file.txt', response=response)
                self.assertEqual(result.stdout.count('(Y/n)'), 1)
                self.assertIn('Cancelled', result.stdout)
                self.assert_file('my file.txt')
                self.assertFalse((self.directory / 'my-file.txt').exists())

    def test_confirmed_recursive_globs_apply_all_proposals_once(self):
        self.create('one file.txt')
        self.create('sub directory/two file.txt')
        self.create('keep file.pdf')
        result = self.run_cli('-r', '--camelcase', '**/*.txt', 'one file.txt', response='\n')
        self.assertEqual(result.stdout.count('(Y/n)'), 1)
        self.assertEqual(result.stdout.count('Proposed:'), 2)
        self.assert_file('OneFile.txt')
        self.assert_file('sub directory/TwoFile.txt')
        self.assert_file('keep file.pdf')

    def test_no_proposals_does_not_prompt(self):
        self.create('safe.txt')
        result = self.run_cli('safe.txt', response='\n')
        self.assertNotIn('(Y/n)', result.stdout)
        self.assertIn('0 files would be renamed', result.stdout)
        self.assert_file('safe.txt')

    def test_wet_mode_bypasses_confirmation(self):
        self.create('my file.txt')
        result = self.run_cli('-w', 'my file.txt', response='n\n')
        self.assertNotIn('(Y/n)', result.stdout)
        self.assert_file('my-file.txt')

    def test_explicit_dry_run_never_prompts_or_writes(self):
        self.create('my file.txt')
        for flag in ('-n', '--dry-run'):
            with self.subTest(flag=flag):
                result = self.run_cli(flag, 'my file.txt', response='\n')
                self.assertNotIn('(Y/n)', result.stdout)
                self.assertIn('[DRY RUN]', result.stdout)
                self.assert_file('my file.txt')
                self.assertFalse((self.directory / 'my-file.txt').exists())

    def test_wet_and_dry_run_are_mutually_exclusive(self):
        self.create('my file.txt')
        self.run_cli('-w', '--dry-run', 'my file.txt', expected=2, response='\n')
        self.assert_file('my file.txt')

    def test_quoted_glob_default_mode(self):
        self.create('first file.txt')
        self.create('second file.txt')
        self.create('keep file.pdf')
        self.run_cli('-w', '*.txt')
        self.assert_file('first-file.txt')
        self.assert_file('second-file.txt')
        self.assert_file('keep file.pdf')
        self.assertFalse((self.directory / 'first file.txt').exists())

    def test_quoted_glob_camelcase(self):
        self.create('first file.txt')
        self.create('second-file_name.txt')
        self.run_cli('--camelcase', '-w', '*.txt')
        self.assert_file('FirstFile.txt')
        self.assert_file('SecondFileName.txt')

    def test_camelcase_dry_run_does_not_write(self):
        self.create('my file.txt')
        result = self.run_cli('--dry-run', '--camelcase', '*.txt')
        self.assertIn('MyFile.txt', result.stdout)
        self.assert_file('my file.txt')
        self.assertFalse((self.directory / 'MyFile.txt').exists())

    def test_multiple_expanded_paths(self):
        self.create('first file.txt')
        self.create('second file.txt')
        self.run_cli('-w', 'first file.txt', 'second file.txt')
        self.assert_file('first-file.txt')
        self.assert_file('second-file.txt')

    def test_multiple_patterns_and_explicit_file(self):
        for name in ('one file.txt', 'two file.pdf', 'three file.csv', 'keep file.zip'):
            self.create(name)
        self.run_cli('-w', '--camelcase', '*.txt', '*.pdf', 'three file.csv')
        for name in ('OneFile.txt', 'TwoFile.pdf', 'ThreeFile.csv', 'keep file.zip'):
            self.assert_file(name)

    def test_question_mark_and_bracket_globs(self):
        for name in ('a 1.txt', 'a 2.txt', 'a 3.txt', 'b 1.txt'):
            self.create(name)
        self.run_cli('-w', '? [12].txt')
        for name in ('a-1.txt', 'a-2.txt', 'a 3.txt', 'b-1.txt'):
            self.assert_file(name)

    def test_existing_bracket_filename_is_literal(self):
        self.create('my [ab].txt')
        self.create('my a.txt')
        self.run_cli('--camelcase', '-w', 'my [ab].txt')
        self.assert_file('MyAb.txt')
        self.assert_file('my a.txt')

    def test_glob_in_directory_with_spaces(self):
        self.create('my directory/my file.txt')
        self.run_cli('--camelcase', '-w', str(self.directory / 'my directory' / '*.txt'))
        self.assert_file('my directory/MyFile.txt')

    def test_nonrecursive_directory_leaves_nested_files_and_directories(self):
        self.create('my directory/my file.txt')
        self.create('my directory/sub directory/nested file.txt')
        self.run_cli('-w', 'my directory')
        self.assert_file('my directory/my-file.txt')
        self.assert_file('my directory/sub directory/nested file.txt')

    def test_recursive_directory_camelcase(self):
        self.create('my directory/my file.txt')
        self.create('my directory/sub directory/nested file.txt')
        self.run_cli('-w', '-r', '--camelcase', 'my directory')
        self.assert_file('my directory/MyFile.txt')
        self.assert_file('my directory/sub directory/NestedFile.txt')

    def test_recursive_glob_includes_root_and_nested_matches_only(self):
        self.create('root file.txt')
        self.create('sub directory/my file.txt')
        self.create('sub directory/keep file.pdf')
        self.run_cli('-r', '-w', '--camelcase', '**/*.txt')
        self.assert_file('RootFile.txt')
        self.assert_file('sub directory/MyFile.txt')
        self.assert_file('sub directory/keep file.pdf')

    def test_directory_glob(self):
        self.create('group one/my file.txt')
        self.create('group two/my file.txt')
        self.run_cli('-w', 'group *')
        self.assert_file('group one/my-file.txt')
        self.assert_file('group two/my-file.txt')

    def test_overlapping_paths_are_processed_once(self):
        self.create('my file.txt')
        result = self.run_cli('-w', '--camelcase', '*.txt', 'my file.txt', '.', '*.txt')
        self.assertEqual(result.stdout.count('Renaming:'), 1)
        self.assertIn('1 files renamed', result.stdout)
        self.assert_file('MyFile.txt')

    def test_unmatched_pattern_is_an_error_and_never_falls_back_to_cwd(self):
        self.create('keep file.txt')
        result = self.run_cli('-w', '*.pdf', expected=1)
        self.assertIn('No files or directories match', result.stderr)
        self.assert_file('keep file.txt')

    def test_missing_path_returns_failure_but_other_paths_still_run(self):
        self.create('my file.txt')
        self.run_cli('-w', 'missing directory', 'my file.txt', expected=1)
        self.assert_file('my-file.txt')

    def test_existing_target_is_never_overwritten(self):
        for camelcase, target in ((False, 'my-file.txt'), (True, 'MyFile.txt')):
            with self.subTest(camelcase=camelcase):
                self.create('my file.txt', 'source')
                self.create(target, 'destination')
                flags = ['--camelcase'] if camelcase else []
                result = self.run_cli('-w', *flags, 'my file.txt', expected=1)
                self.assertIn('already exists', result.stderr)
                self.assert_file('my file.txt', 'source')
                self.assert_file(target, 'destination')
                (self.directory / target).unlink()

    def test_two_sources_for_one_target_conflict_in_preview_and_wet_run(self):
        self.create('my file.txt', 'first')
        self.create('my_file.txt', 'second')
        preview = self.run_cli('--camelcase', '*.txt', expected=1)
        self.assertIn('1 files would be renamed', preview.stdout)
        self.assert_file('my file.txt', 'first')
        self.assert_file('my_file.txt', 'second')
        self.run_cli('-w', '--camelcase', '*.txt', expected=1)
        self.assert_file('MyFile.txt', 'first')
        self.assert_file('my_file.txt', 'second')

    def test_case_only_rename(self):
        self.create('myFile.txt')
        self.run_cli('-w', '--camelcase', 'myFile.txt')
        self.assertIn('MyFile.txt', os.listdir(self.directory))
        self.assert_file('MyFile.txt')

    def test_quiet_suppresses_success_output_but_preserves_errors(self):
        self.create('my file.txt')
        preview = self.run_cli('-q', '--camelcase', '*.txt')
        self.assertEqual(preview.stdout + preview.stderr, '')
        self.assert_file('my file.txt')
        result = self.run_cli('-q', '-w', '--camelcase', '*.txt')
        self.assertEqual(result.stdout + result.stderr, '')
        failure = self.run_cli('-q', '*.pdf', expected=1)
        self.assertEqual(failure.stdout, '')
        self.assertIn('Error:', failure.stderr)

    def test_filename_starting_with_hyphen(self):
        self.create('-my file.txt')
        self.run_cli('-w', '--camelcase', '--', '-my file.txt')
        self.assert_file('MyFile.txt')

    def test_invalid_option_returns_usage_error(self):
        result = self.run_cli('--not-an-option', expected=2)
        self.assertIn('usage:', result.stderr)

    def test_empty_directory_succeeds(self):
        result = self.run_cli('-w', '--camelcase')
        self.assertIn('0 files renamed', result.stdout)

    def test_unicode_filename_round_trip(self):
        self.create('café 東京：my file.txt')
        self.run_cli('-w', '--camelcase', '*.txt')
        self.assert_file('Café東京MyFile.txt')

    def test_second_camelcase_run_is_unchanged(self):
        self.create('my file.tar.gz')
        self.run_cli('-w', '--camelcase')
        result = self.run_cli('-w', '--camelcase')
        self.assertIn('0 files renamed', result.stdout)
        self.assert_file('MyFile.tar.gz')

    def test_existing_directory_target_is_not_overwritten(self):
        self.create('my file.txt')
        (self.directory / 'MyFile.txt').mkdir()
        self.run_cli('-w', '--camelcase', 'my file.txt', expected=1)
        self.assert_file('my file.txt')
        self.assertTrue((self.directory / 'MyFile.txt').is_dir())

    def test_distinct_case_variant_target_is_not_overwritten(self):
        self.create('myFile.txt', 'source')
        target = self.directory / 'MyFile.txt'
        if target.exists():
            self.skipTest('Filesystem is case-insensitive; covered by case-only rename test')
        self.create('MyFile.txt', 'destination')
        self.run_cli('-w', '--camelcase', 'myFile.txt', expected=1)
        self.assert_file('myFile.txt', 'source')
        self.assert_file('MyFile.txt', 'destination')

    def test_existing_hardlink_target_is_not_overwritten(self):
        source = self.create('myFile.txt')
        target = self.directory / 'MyFile.txt'
        if target.exists():
            self.skipTest('Distinct case variants require a case-sensitive filesystem')
        try:
            os.link(source, target)
        except OSError as error:
            self.skipTest(f'Hardlinks unavailable: {error}')
        self.run_cli('-w', '--camelcase', 'myFile.txt', expected=1)
        self.assert_file('myFile.txt')
        self.assert_file('MyFile.txt')

    @unittest.skipIf(os.name == 'nt', 'Windows disallows these source filename characters')
    def test_windows_invalid_characters_in_real_posix_files(self):
        self.create('my:file?name*.txt')
        self.run_cli('-w', '--camelcase', '*.txt')
        self.assert_file('MyFileName.txt')

    @unittest.skipIf(os.name == 'nt', 'Windows symlinks may require additional privileges')
    def test_broken_symlink_target_is_not_overwritten(self):
        self.create('my file.txt')
        (self.directory / 'MyFile.txt').symlink_to('missing')
        self.run_cli('-w', '--camelcase', 'my file.txt', expected=1)
        self.assert_file('my file.txt')
        self.assertTrue((self.directory / 'MyFile.txt').is_symlink())


class ErrorHandlingTests(FilesystemTestCase):
    def test_interrupt_at_confirmation_cancels(self):
        source = self.create('my file.txt')
        with mock.patch('builtins.input', side_effect=KeyboardInterrupt):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                result = filerenamer.rename_files(source, confirm=True)
        self.assertEqual(result, 0)
        self.assertIn('Cancelled', output.getvalue())
        self.assert_file('my file.txt')
        self.assertFalse((self.directory / 'my-file.txt').exists())

    def test_confirmation_only_applies_files_in_the_preview(self):
        source = self.create('my file.txt')

        def confirm(prompt):
            self.create('new file.txt')
            return ''

        with mock.patch('builtins.input', side_effect=confirm):
            with contextlib.redirect_stdout(io.StringIO()):
                result = filerenamer.rename_files(self.directory / '*.txt', confirm=True)
        self.assertEqual(result, 0)
        self.assertFalse(source.exists())
        self.assert_file('my-file.txt')
        self.assert_file('new file.txt')
        self.assertFalse((self.directory / 'new-file.txt').exists())

    def test_destination_created_during_confirmation_is_not_overwritten(self):
        source = self.create('my file.txt')

        def confirm(prompt):
            self.create('my-file.txt', 'created while waiting')
            return 'Y'

        with mock.patch('builtins.input', side_effect=confirm):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = filerenamer.rename_files(source, confirm=True)
        self.assertEqual(result, 1)
        self.assert_file('my file.txt')
        self.assert_file('my-file.txt', 'created while waiting')

    def test_rename_failure_returns_error_and_continues(self):
        source = self.create('my file.txt')
        with mock.patch.object(Path, 'rename', side_effect=PermissionError('access denied')):
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                result = filerenamer.rename_files(source, dry_run=False, verbose=False)
        self.assertEqual(result, 1)
        self.assertIn('access denied', errors.getvalue())
        self.assert_file('my file.txt')

    def test_unreadable_directory_returns_error(self):
        with mock.patch.object(Path, 'iterdir', side_effect=PermissionError('access denied')):
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                result = filerenamer.rename_files(self.directory, verbose=False)
        self.assertEqual(result, 1)
        self.assertIn('access denied', errors.getvalue())


class LauncherTests(FilesystemTestCase):
    def setUp(self):
        super().setUp()
        # Run a relocated copy to catch hardcoded paths and quoting bugs.
        self.install = self.directory / 'installation with spaces'
        self.install.mkdir()
        for name in ('filerenamer.py', 'filerenamer', 'filerenamer.bat'):
            shutil.copy2(ROOT / name, self.install / name)

    def test_recorded_build_time_is_independent_of_runtime_clock_and_file_mtime(self):
        script = self.install / 'filerenamer.py'
        os.utime(script, (946684800, 946684800))
        for timezone in ('UTC0', 'EST5'):
            with self.subTest(timezone=timezone):
                result = subprocess.run([sys.executable, str(script), '--version'],
                                        cwd=self.directory, env=dict(os.environ, TZ=timezone),
                                        input='', capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, filerenamer.BUILD_TIME + '\n')

    @unittest.skipIf(os.name == 'nt', 'POSIX shell launcher')
    def test_shell_launcher_version(self):
        result = subprocess.run(['sh', str(self.install / 'filerenamer'), '--version'],
                                cwd=self.directory, input='', capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, filerenamer.BUILD_TIME + '\n')

    @unittest.skipIf(os.name == 'nt', 'POSIX shell launcher')
    def test_shell_launcher_quoted_and_expanded_globs(self):
        self.create('one file.txt')
        self.create('two file.txt')
        result = subprocess.run(['sh', str(self.install / 'filerenamer'), '--camelcase', '*.txt'],
                                cwd=self.directory, input='', capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('2 files would be renamed', result.stdout)
        result = subprocess.run(['sh', '-c', 'sh "$1" -w --camelcase *.txt', 'test',
                                 str(self.install / 'filerenamer')], cwd=self.directory,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_file('OneFile.txt')
        self.assert_file('TwoFile.txt')

    @unittest.skipIf(os.name == 'nt', 'POSIX shell launcher')
    def test_shell_launcher_help_and_exit_code(self):
        for args, expected in ((['--help'], 0), (['*.missing'], 1), (['--bad-option'], 2)):
            with self.subTest(args=args):
                result = subprocess.run(['sh', str(self.install / 'filerenamer'), *args],
                                        cwd=self.directory, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                if expected == 0:
                    self.assertIn('--camelcase', result.stdout)

    @unittest.skipIf(os.name == 'nt', 'POSIX shell launcher')
    def test_shell_launcher_confirmation(self):
        self.create('my file.txt')
        for response in ('n\n', '\n'):
            with self.subTest(response=repr(response)):
                result = subprocess.run(['sh', str(self.install / 'filerenamer'), 'my file.txt'],
                                        cwd=self.directory, input=response, capture_output=True,
                                        text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('(Y/n)', result.stdout)
                self.assert_file('my file.txt' if response == 'n\n' else 'my-file.txt')

    def run_cmd(self, arguments, response=''):
        # CMD's outer quotes protect the quoted batch path; its wildcards stay literal.
        cmd = os.environ.get('COMSPEC', 'cmd.exe')
        command = f'"{cmd}" /d /s /c ""{self.install / "filerenamer.bat"}" {arguments}"'
        return subprocess.run(command,
                              cwd=self.directory, input=response, capture_output=True, text=True, timeout=30)

    @unittest.skipUnless(os.name == 'nt', 'Requires native Windows CMD; covered by CI')
    def test_cmd_launcher_version(self):
        result = self.run_cmd('--version')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, filerenamer.BUILD_TIME + '\n')

    @unittest.skipUnless(os.name == 'nt', 'Requires native Windows CMD; covered by CI')
    def test_cmd_launcher_confirmation(self):
        self.create('my file.txt')
        for response in ('n\n', '\n'):
            with self.subTest(response=repr(response)):
                result = self.run_cmd('"my file.txt"', response=response)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('(Y/n)', result.stdout)
                self.assert_file('my file.txt' if response == 'n\n' else 'my-file.txt')

    @unittest.skipUnless(os.name == 'nt', 'Requires native Windows CMD; covered by CI')
    def test_cmd_launcher_unquoted_globs(self):
        self.create('one file.txt')
        self.create('two file.txt')
        result = self.run_cmd('-w --camelcase *.txt')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_file('OneFile.txt')
        self.assert_file('TwoFile.txt')

    @unittest.skipUnless(os.name == 'nt', 'Requires native Windows CMD; covered by CI')
    def test_cmd_launcher_quoted_globs_and_multiple_paths(self):
        self.create('one file.txt')
        self.create('two file.pdf')
        result = self.run_cmd('-w --camelcase "*.txt" "two file.pdf"')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_file('OneFile.txt')
        self.assert_file('TwoFile.pdf')

    @unittest.skipUnless(os.name == 'nt', 'Requires native Windows CMD; covered by CI')
    def test_cmd_launcher_help_and_exit_codes(self):
        for args, expected in (('--help', 0), ('*.missing', 1), ('--bad-option', 2)):
            with self.subTest(args=args):
                result = self.run_cmd(args)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                if expected == 0:
                    self.assertIn('--camelcase', result.stdout)


if __name__ == '__main__':
    unittest.main()
