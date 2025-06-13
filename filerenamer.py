#!/usr/bin/env python3
"""
File Renamer Script
Replaces problematic characters in filenames with safe alternatives.
Works on both Windows and WSL/Linux.
"""

import os
import sys
import argparse
from pathlib import Path

# Character replacement mapping
CHAR_MAP = {
    ':': '_',
    '：': '_',  # Fullwidth colon (U+FF1A)
    ',': '-',
    '，': '-',  # Fullwidth comma
    ' ': '-',
    '　': '-',  # Fullwidth space
    ';': '_',
    '；': '_',  # Fullwidth semicolon
    '?': '_',
    '？': '_',  # Fullwidth question mark
    '<': '_',
    '＜': '_',  # Fullwidth less-than
    '>': '_',
    '＞': '_',  # Fullwidth greater-than
    '|': '_',
    '｜': '_',  # Fullwidth vertical bar
    '"': '_',
    '"': '_',  # Left double quotation mark
    '"': '_',  # Right double quotation mark
    ''': '_',  # Left single quotation mark
    ''': '_',  # Right single quotation mark (apostrophe)
    '*': '_',
    '＊': '_',  # Fullwidth asterisk
    '/': '_',
    '／': '_',  # Fullwidth slash
    '\\': '_',
    '＼': '_'  # Fullwidth backslash
}

def sanitize_filename(filename):
    """Replace problematic characters in filename according to CHAR_MAP."""
    for old_char, new_char in CHAR_MAP.items():
        filename = filename.replace(old_char, new_char)
    
    # Remove multiple consecutive dashes or underscores
    while '--' in filename:
        filename = filename.replace('--', '-')
    while '__' in filename:
        filename = filename.replace('__', '_')
    
    return filename

def rename_files(path, recursive=False, dry_run=True, verbose=True):
    """
    Rename files in the specified path.
    
    Args:
        path: Directory path to process
        recursive: Process subdirectories recursively
        dry_run: Show what would be renamed without actually renaming
        verbose: Print detailed output
    """
    path = Path(path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.")
        return
    
    files_renamed = 0
    
    # Get files to process
    if path.is_file():
        files_to_process = [path]
    elif recursive:
        files_to_process = [f for f in path.rglob('*') if f.is_file()]
    else:
        files_to_process = [f for f in path.iterdir() if f.is_file()]
    
    for file_path in files_to_process:
        old_name = file_path.name
        new_name = sanitize_filename(old_name)
        
        if old_name != new_name:
            new_path = file_path.parent / new_name
            
            if verbose:
                print(f"{'[DRY RUN] ' if dry_run else ''}Renaming: {old_name} -> {new_name}")
            
            if not dry_run:
                # Check if target already exists
                if new_path.exists():
                    print(f"  Warning: '{new_name}' already exists. Skipping.")
                    continue
                
                try:
                    file_path.rename(new_path)
                    files_renamed += 1
                except Exception as e:
                    print(f"  Error renaming '{old_name}': {e}")
            else:
                # In dry-run mode, count the file unless target exists
                if not new_path.exists():
                    files_renamed += 1
                elif verbose:
                    print(f"  Warning: '{new_name}' already exists. Would skip.")
    
    if verbose:
        if dry_run:
            print(f"\nDry run complete. {files_renamed} files would be renamed.")
        else:
            print(f"\nComplete. {files_renamed} files renamed.")

def main():
    parser = argparse.ArgumentParser(
        description='Rename files by replacing problematic characters.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Character replacements:
  : -> _
  , -> -
  space -> -
  ; -> _
  ? -> _
  < -> _
  > -> _
  | -> _
  " -> _
  * -> _
  / -> _
  \\ -> _

Examples:
  %(prog)s .                    # Dry-run: show what would be renamed
  %(prog)s -w .                 # Actually rename files in current directory
  %(prog)s /path/to/dir         # Dry-run in specific directory
  %(prog)s -w -r /path/to/dir   # Recursively rename files (wet run)
  %(prog)s -r /path/to/dir      # Recursive dry-run
        """
    )
    
    parser.add_argument('path', nargs='?', default='.',
                        help='Path to directory or file (default: current directory)')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='Process subdirectories recursively')
    parser.add_argument('-w', '--wet', action='store_true',
                        help='Actually rename files (default is dry-run)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress output except errors')
    
    args = parser.parse_args()
    
    rename_files(
        path=args.path,
        recursive=args.recursive,
        dry_run=not args.wet,
        verbose=not args.quiet
    )

if __name__ == '__main__':
    main()