# File Renamer

A cross-platform Python script that eliminates spaces and problematic characters from filenames, making them safe for use across Windows, Linux, and other systems.

## Features

- Replaces problematic characters in filenames with safe alternatives
- Works on Windows, WSL, and Linux
- Dry-run mode by default (safe operation)
- Recursive directory processing
- Handles Unicode characters (fullwidth colons, etc.)

## Character Replacements

| Character | Replacement | Description |
|-----------|-------------|-------------|
| `:` `：` | `_` | Colon (regular and fullwidth) |
| `,` `，` | `-` | Comma (regular and fullwidth) |
| ` ` `　` | `-` | Space (regular and fullwidth) |
| `;` `；` | `_` | Semicolon (regular and fullwidth) |
| `?` `？` | `_` | Question mark (regular and fullwidth) |
| `<` `>` | `_` | Angle brackets |
| `|` `｜` | `_` | Pipe/vertical bar |
| `"` `"` `"` | `_` | Various quotation marks |
| `'` `'` | `_` | Apostrophes and single quotes |
| `*` `＊` | `_` | Asterisk |
| `/` `／` `\` `＼` | `_` | Slashes |

## Installation

### Quick Setup

The script requires Python 3 and uses only standard library modules (no dependencies).

#### Windows Setup

1. Create a batch file wrapper in `C:\core\installations\filerenamer.bat`:
```batch
@echo off
python "C:\q\arc\projects\filerenamer\filerenamer.py" %*
```

2. Copy the batch file to your PATH:
```cmd
copy filerenamer.bat C:\core\installations\
```

#### WSL/Linux Setup

1. Create a shell script wrapper in `/home/user/bin/filerenamer`:
```bash
#!/bin/bash
python3 /mnt/c/q/arc/projects/filerenamer/filerenamer.py "$@"
```

2. Make it executable and copy to your PATH:
```bash
chmod +x filerenamer
cp filerenamer /home/user/bin/
```

## Usage

### Basic Commands

```bash
# Dry-run (default) - shows what would be renamed
filerenamer                    # Current directory
filerenamer /path/to/dir       # Specific directory

# Actually rename files (requires -w flag)
filerenamer -w                 # Current directory
filerenamer -w /path/to/dir    # Specific directory

# Recursive operation
filerenamer -r                 # Dry-run recursively
filerenamer -w -r              # Rename recursively

# Quiet mode (only show errors)
filerenamer -q -w
```

### Command Line Options

- `-w, --wet` - Actually rename files (default is dry-run)
- `-r, --recursive` - Process subdirectories recursively
- `-q, --quiet` - Suppress output except errors
- `path` - Directory or file to process (default: current directory)

### Examples

```bash
# Preview changes in current directory
filerenamer

# Preview changes recursively
filerenamer -r /mnt/c/Downloads

# Actually rename files in a specific directory
filerenamer -w ~/Documents

# Rename a single file
filerenamer -w "My File：With Special，Characters.txt"
```

## Safety Features

- **Dry-run by default**: The script shows what would be changed without actually renaming
- **Duplicate detection**: Skips files if the target filename already exists
- **Error handling**: Continues processing other files if one fails

## Notes

- Last updated: 2025-01-13
- The script handles both ASCII and Unicode problematic characters
- Consecutive dashes or underscores are consolidated to single characters
- Original files are renamed in-place (no copies are made)

## Future Enhancements

More robust installation options with support for arbitrary paths across Windows, WSL, and Cygwin environments will be implemented separately.