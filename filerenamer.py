#!/usr/bin/env python3
"""Propose portable filenames and confirm before renaming or copying files."""

import argparse
import glob
import os
from pathlib import Path
import re
import shutil
import sys
import unicodedata


# Updated by build.py; package builds stamp their own copy using the host clock.
BUILD_TIME = "2026-10-05_23-36-00"


CHAR_MAP = dict.fromkeys(':：;；?？<＜>＞|｜"“”\'‘’*＊/／\\＼', '_')
CHAR_MAP.update(dict.fromkeys(',， \u3000', '-'))
WINDOWS_RESERVED_NAMES = {'CON', 'PRN', 'AUX', 'NUL'} | {
    prefix + number for prefix in ('COM', 'LPT') for number in '123456789¹²³'
}


def _is_word_character(character):
    # Keep Unicode letters, numbers and combining marks (including accents).
    return unicodedata.category(character)[0] in 'LNM'


def _camelcase(filename, preserve_extension=False, preserve_initial=False):
    if not preserve_extension:
        filename = filename.rstrip(' .')
    hidden = filename.startswith('.')
    filename = filename.lstrip('.')
    # Keep extension chains such as .tar.gz, including their original case.
    stem, dot, extension = filename.partition('.')
    words = ''.join(c if _is_word_character(c) else ' ' for c in stem).split()
    stem = ''.join(
        word if preserve_initial and index == 0 else word[:1].upper() + word[1:]
        for index, word in enumerate(words)
    ) or 'File'
    if not preserve_extension:
        extension = '.'.join(
            cleaned for part in extension.split('.')
            if (cleaned := ''.join(c for c in part if _is_word_character(c)))
        )
        dot = '.' if extension else ''
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem += 'File'
    return ('.' if hidden else '') + stem + dot + extension


def sanitize_filename(filename, camelcase=False):
    """Sanitize a basename, preserving extensions and avoiding Windows devices."""
    if camelcase:
        return _camelcase(filename)
    filename = ''.join(
        '_' if ord(c) < 32 else CHAR_MAP.get(c, '-' if c.isspace() else c)
        for c in filename
    )
    filename = re.sub(r'-+', '-', re.sub(r'_+', '_', filename)).rstrip(' .')
    filename = filename or 'File'
    if filename.partition('.')[0].upper() in WINDOWS_RESERVED_NAMES:
        filename = '_' + filename
    return filename


def collect_files(paths, recursive=False):
    """Expand patterns before renaming and process overlapping selections once."""
    files = []
    seen = set()
    errors = 0
    for raw_path in paths:
        pattern = os.path.expanduser(os.fspath(raw_path))
        path = Path(pattern)
        matches = [path] if path.exists() else [
            Path(match) for match in sorted(glob.glob(pattern, recursive=recursive))
        ]
        if not matches:
            print(f"Error: No files or directories match '{raw_path}'.", file=sys.stderr)
            errors += 1
        for match in matches:
            try:
                if match.is_file():
                    candidates = [match]
                elif match.is_dir():
                    entries = match.rglob('*') if recursive else match.iterdir()
                    candidates = sorted(f for f in entries if f.is_file())
                else:
                    print(f"Error: '{match}' is not a file or directory.", file=sys.stderr)
                    errors += 1
                    continue
                for candidate in candidates:
                    key = os.path.normcase(os.path.abspath(candidate))
                    if key not in seen:
                        seen.add(key)
                        files.append(candidate)
            except OSError as error:
                print(f"Error reading '{match}': {error}", file=sys.stderr)
                errors += 1
    return files, errors


def _same_directory_entry(source, target):
    """Allow case-only changes on case-insensitive disks, but never merge hardlinks."""
    if source.name.casefold() != target.name.casefold():
        return False
    try:
        return source.samefile(target) and target.name not in os.listdir(source.parent)
    except OSError:
        return False


def get_user_confirmation(action='renaming'):
    """Only Enter, y, or Y confirms; all other input (including EOF) cancels."""
    try:
        return input(f'Proceed with {action} these files? (Y/n): ') in ('', 'y', 'Y')
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _copy_file(source, target):
    """Copy contents and metadata, exclusively creating the destination."""
    with source.open('rb') as original:
        duplicate = target.open('xb')
        try:
            with duplicate:
                shutil.copyfileobj(original, duplicate)
            shutil.copystat(source, target)
        except OSError:
            target.unlink()
            raise


def rename_paths(paths, recursive=False, dry_run=True, verbose=True, camelcase=False,
                 confirm=False, camelcase_copy=False):
    camelcase = camelcase or camelcase_copy
    action = 'copying' if camelcase_copy else 'renaming'
    completed_action = 'copied' if camelcase_copy else 'renamed'
    files, errors = collect_files(paths, recursive)
    proposals = []
    planned = set()
    for source in files:
        new_name = (_camelcase(source.name, preserve_extension=True, preserve_initial=True)
                    if camelcase_copy
                    else sanitize_filename(source.name, camelcase=camelcase))
        if new_name == source.name and not camelcase_copy:
            continue
        target = source.with_name(new_name)
        # Keep extension chains and hidden-file prefixes when numbering conflicts.
        extension = (''.join(source.name.lstrip('.').partition('.')[1:]) if camelcase_copy
                     else ''.join(target.suffixes))
        stem = new_name[:-len(extension)] if extension else new_name
        separator = '' if camelcase else '_'
        counter = 0
        while True:
            key = os.path.normcase(os.path.abspath(target))
            # Windows and macOS often use case-insensitive filesystems.
            occupied = os.path.lexists(target) and (
                camelcase_copy or not _same_directory_entry(source, target))
            if key not in planned and not occupied:
                break
            counter += 1
            target = source.with_name(f'{stem}{separator}{counter}{extension}')
        planned.add(key)
        proposals.append((source, target))
        if dry_run and verbose:
            label = 'Proposed copy' if camelcase_copy else 'Proposed'
            if not confirm:
                label = f'[DRY RUN] {action.capitalize()}'
            print(f'{label}: {source} -> {target}')

    if dry_run:
        if verbose:
            print(f"{'Preview' if confirm else 'Dry run'} complete. "
                  f"{len(proposals)} files would be {completed_action}.")
        if not confirm or not proposals:
            return 1 if errors else 0
        if not get_user_confirmation(action):
            if verbose:
                print(f'Cancelled. No files {completed_action}.')
            return 1 if errors else 0

    # Apply the exact proposals that were shown, without expanding globs again.
    completed = 0
    for source, target in proposals:
        if os.path.lexists(target) and (
                camelcase_copy or not _same_directory_entry(source, target)):
            print(f"Error: Skipping '{source}': target '{target}' already exists.",
                  file=sys.stderr)
            errors += 1
            continue
        if verbose:
            print(f'{action.capitalize()}: {source} -> {target}')
        try:
            if camelcase_copy:
                _copy_file(source, target)
            else:
                source.rename(target)
            completed += 1
        except OSError as error:
            print(f"Error {action} '{source}': {error}", file=sys.stderr)
            errors += 1
    if verbose:
        print(f'Complete. {completed} files {completed_action}.')
    return 1 if errors else 0


def rename_files(path, recursive=False, dry_run=True, verbose=True, camelcase=False,
                 confirm=False, camelcase_copy=False):
    """Rename or copy files selected by one file, directory or wildcard pattern."""
    return rename_paths([path], recursive, dry_run, verbose, camelcase, confirm,
                        camelcase_copy)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Propose Windows-friendly filenames, then ask before renaming or copying.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Confirmation:
  By default, preview all proposed names, then ask once: proceed? (Y/n).
  Press Enter, y, or Y to apply those changes. Any other input cancels and exits.
  Closed input (EOF) or Ctrl+C at the prompt also cancels.
  Use -w to apply immediately, or -n/--dry-run to preview without prompting.
  Quiet mode does not prompt; combine -q with -w to apply changes.

Naming modes:
  Default: spaces/commas become hyphens; other problematic characters become
  underscores. Repeated hyphens or underscores are collapsed.
  --camelcase: "my file: name.txt" becomes "MyFileName.txt". Spaces and
  punctuation (including hyphens/underscores) separate words and are removed.
  Existing capitals and Unicode letters are kept. Extensions (e.g. .tar.gz)
  keep their case; punctuation/spaces within extensions are removed.
  Windows device names (CON, NUL, etc.) are made safe in both modes.
  --camelcase-copy: create CamelCase copies beside the originals, leaving the
  original files in place. Preserve the initial letter's case and capitalize
  later words: "my example-file.txt" becomes "myExampleFile.txt".
  Keep extensions exactly unchanged (including extension chains).
  Existing destinations and already-CamelCase names get numbered copies,
  such as MyFile1.txt, MyFile2.txt, etc. Existing files are never overwritten.

Paths and wildcards:
  Accepts multiple files, directories, and patterns (*, ?, [abc]).
  Quote patterns for consistent WSL/Linux and CMD behavior: "*.txt".
  Shell-expanded patterns also work. Use -r with "**/*.txt" to match recursively.
  Directory paths process files only; -r includes subdirectories.
  Existing literal paths take priority over wildcard expansion.
  Use -- before filenames that start with a hyphen.
  Conflicts use numbered alternatives: name_1.txt, name_2.txt, etc. CamelCase
  uses Name1.txt, Name2.txt, etc. The preview shows the available names.
  No matches, file operation errors, and targets occupied after preview return
  exit status 1; invalid usage returns 2. Dry runs never write.

Examples (WSL/Linux and Windows CMD):
  %(prog)s --help
  %(prog)s --version                       Print the recorded local build time
  %(prog)s "*.txt"                         Propose names and ask to proceed
  %(prog)s --camelcase "*.txt"              Propose CamelCase names and confirm
  %(prog)s --camelcase-copy "*.txt"         Propose CamelCase copies and confirm
  %(prog)s -w --camelcase-copy "*.txt"      Create CamelCase copies immediately
  %(prog)s -n --camelcase "*.txt"           Preview only, without prompting
  %(prog)s -w --camelcase "*.txt" "*.pdf"   Apply changes to two patterns
  %(prog)s -w -r "path to directory"        Rename files recursively
  %(prog)s -r --camelcase "**/*.txt"        Propose recursive matches and confirm
  %(prog)s -w -- "-my file.txt"             Rename a leading-hyphen file
''')
    parser.add_argument('--version', action='version', version=BUILD_TIME,
                        help='Print local build time (yyyy-mm-dd_hh-mm-ss, 24-hour) and exit')
    parser.add_argument('paths', nargs='*', default=['.'], metavar='PATH',
                        help='Files, directories, or wildcard patterns (default: current directory)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Include subdirectories; enable recursive ** patterns')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('-w', '--wet', action='store_true',
                      help='Apply renames or copies immediately without confirmation')
    mode.add_argument('-n', '--dry-run', action='store_true',
                      help='Preview only, without prompting or changing files')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress output and prompts except errors; requires -w to write')
    parser.add_argument('--camelcase', action='store_true',
                        help='Join words in CamelCase without spaces, hyphens, or underscores')
    parser.add_argument('--camelcase-copy', action='store_true',
                        help='Copy with CamelCase names, preserving the initial letter case and originals')
    args = parser.parse_args(argv)
    return rename_paths(args.paths, recursive=args.recursive, dry_run=not args.wet,
                        verbose=not args.quiet, camelcase=args.camelcase,
                        confirm=not (args.wet or args.dry_run or args.quiet),
                        camelcase_copy=args.camelcase_copy)


if __name__ == '__main__':
    sys.exit(main())
