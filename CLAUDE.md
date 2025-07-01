# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform Python file renaming utility that sanitizes filenames by replacing problematic characters with safe alternatives. The project consists of:

- `filerenamer.py` - Main Python script with character mapping and file processing logic
- `filerenamer.bat` - Windows batch wrapper for easy command-line access
- `filerenamer` - Linux/WSL shell wrapper for easy command-line access

## Usage

The script operates in dry-run mode by default for safety:

```bash
# Dry-run (shows what would be renamed)
python filerenamer.py
python filerenamer.py /path/to/directory

# Actually rename files (requires -w flag)
python filerenamer.py -w
python filerenamer.py -w /path/to/directory

# Recursive processing
python filerenamer.py -r -w /path/to/directory

# Quiet mode (errors only)
python filerenamer.py -q -w
```

## Architecture

### Core Components

- **Character Mapping (`CHAR_MAP`)**: Dictionary defining problematic characters and their safe replacements, including Unicode variants (fullwidth characters)
- **`sanitize_filename()`**: Core function that applies character replacements and consolidates consecutive separators
- **`rename_files()`**: Main processing function that handles directory traversal, dry-run logic, and error handling

### Key Features

- Dry-run by default (must use `-w` flag to actually rename)
- Handles both ASCII and Unicode problematic characters
- Recursive directory processing with `-r` flag
- Duplicate filename detection and skipping
- Cross-platform compatibility (Windows/WSL/Linux)

### Character Replacement Strategy

The script replaces various problematic characters:
- Colons/semicolons → underscore (`_`)
- Commas/spaces → dash (`-`)
- Quotes/brackets/pipes → underscore (`_`)
- Slashes/asterisks → underscore (`_`)

Consecutive dashes or underscores are consolidated to single characters.

## Dependencies

None - uses only Python 3 standard library modules (`os`, `sys`, `argparse`, `pathlib`).

## Installation

The project includes wrapper scripts for easy system-wide access:
- Windows: Place `filerenamer.bat` in PATH, update hardcoded Python script path
- WSL/Linux: Place `filerenamer` shell script in PATH, update hardcoded Python script path