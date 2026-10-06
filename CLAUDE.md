# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform Python file renaming utility that sanitizes filenames by replacing problematic characters with safe alternatives. The project consists of:

- `filerenamer.py` - Main Python script with character mapping and file processing logic
- `filerenamer.bat` - Windows batch wrapper for easy command-line access
- `filerenamer` - Linux/WSL shell wrapper for easy command-line access
- `pyproject.toml` - Pure Python wheel and installed CLI configuration
- `build.py` - Runs tests before building the wheel
- `build_stamp.py` / `setup.py` - Embed local host build time in source/wheel builds
- `tests/` - Standard-library unit, CLI, and native launcher tests

## Usage

The script proposes renames and asks for confirmation by default:

```bash
# Propose names, then confirm with Enter, y, or Y (anything else cancels)
python filerenamer.py
python filerenamer.py /path/to/directory

# Preview only, without prompting
python filerenamer.py --dry-run /path/to/directory

# Rename immediately without confirmation
python filerenamer.py -w
python filerenamer.py -w /path/to/directory

# Recursive processing
python filerenamer.py -r -w /path/to/directory

# Quiet mode (errors only)
python filerenamer.py -q -w

# CamelCase and wildcard patterns (quote for consistent shell behavior)
python filerenamer.py --camelcase "*.txt"
python filerenamer.py -w --camelcase "*.txt" "*.pdf"

# Full usage information
python filerenamer.py --help
python filerenamer.py --version  # Local build time: yyyy-mm-dd_hh-mm-ss (24-hour)
```

## Architecture

### Core Components

- **Character Mapping (`CHAR_MAP`)**: Dictionary defining problematic characters and their safe replacements, including Unicode variants (fullwidth characters)
- **`sanitize_filename()`**: Core function that applies character replacements and consolidates consecutive separators
- **`rename_files()`**: Main processing function that handles directory traversal, dry-run logic, and error handling

### Key Features

- Propose and confirm by default; only Enter, y, or Y accepts
- Use `-w` to rename immediately or `-n`/`--dry-run` for a noninteractive preview
- Handles both ASCII and Unicode problematic characters
- Recursive directory processing with `-r` flag
- Duplicate filename detection and skipping (errors return status 1)
- Cross-platform compatibility (Windows/WSL/Linux)
- Multiple files/directories and Python-expanded wildcard patterns
- CamelCase mode preserves Unicode letters, existing capitals, and extensions
- Explicit dry-run never prompts or writes; conflicts never prompt for alternative names
- Quiet mode never prompts and requires `-w` to write
- EOF and Ctrl+C at confirmation cancel; confirmed runs use the exact previewed proposals

### Character Replacement Strategy

The script replaces various problematic characters:
- Colons/semicolons → underscore (`_`)
- Commas/spaces → dash (`-`)
- Quotes/brackets/pipes → underscore (`_`)
- Slashes/asterisks → underscore (`_`)

Consecutive dashes or underscores are consolidated to single characters.

## Dependencies

Python 3.9+; no runtime or test dependencies outside the standard library.
Building needs pip, setuptools, and wheel.

## Installation

Install with `python -m pip install .` to create a platform-native `filerenamer`
command. For checkout-based use, keep each wrapper beside `filerenamer.py` and
add that directory to PATH; there are no hardcoded installation paths.

## Validation and Build

Use `python3` in WSL/Linux, or `py -3` in Windows CMD:

```bash
python3 -m unittest discover -s tests -v
python3 build.py
```

`build.py` stops on test failures, then builds `dist/filerenamer-1.0.0-py3-none-any.whl`.
It stamps `filerenamer.py` with the current local host time before running tests
and passes that timestamp to the wheel build. Direct pip source builds stamp
the packaged module through `setup.py`. `--version` prints only the embedded
build timestamp; never compute it from the clock or file mtime at runtime.
Use `--no-build-isolation` for offline builds with setuptools/wheel preinstalled.
GitHub Actions runs the build on Linux, Windows, and macOS with Python 3.9 and
3.14, then installs and smoke-tests the wheel outside the repository.
