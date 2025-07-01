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

def get_alternative_filename(path, base_name):
    """Generate alternative filename if conflict exists."""
    counter = 1
    name_parts = base_name.rsplit('.', 1)
    
    if len(name_parts) == 2:
        name, ext = name_parts
        while (path.parent / f"{name}_{counter}.{ext}").exists():
            counter += 1
        return f"{name}_{counter}.{ext}"
    else:
        while (path.parent / f"{base_name}_{counter}").exists():
            counter += 1
        return f"{base_name}_{counter}"

def get_user_confirmation(prompt):
    """Get Y/n confirmation from user."""
    import sys
    
    # Always display the prompt message first
    print(f"{prompt} (Y/n): ", end='', flush=True)
    
    try:
        response = input().strip().lower()
        if response in ['', 'y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter Y/y/yes or N/n/no (or press Enter for Yes)")
            return get_user_confirmation(prompt)
    except (EOFError, KeyboardInterrupt):
        # In batch/drag-drop context, auto-confirm
        print("Y")
        return True

def rename_files(path, recursive=False, dry_run=True, verbose=True, first_call=True):
    """
    Rename files in the specified path.
    
    Args:
        path: Directory path to process
        recursive: Process subdirectories recursively
        dry_run: Show what would be renamed without actually renaming
        verbose: Print detailed output
        first_call: Whether this is the first call (for "== " prefix)
    """
    path = Path(path)
    
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.")
        return
    
    files_renamed = 0
    first_output = True
    
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
                prefix = "== " if first_call and first_output else ""
                first_output = False
                print(f"{prefix}{'[DRY RUN] ' if dry_run else ''}Renaming: {old_name} -> {new_name}")
            
            if not dry_run:
                # Check if target already exists
                if new_path.exists():
                    print(f"  Warning: '{new_name}' already exists.")
                    alternative_name = get_alternative_filename(file_path, new_name)
                    if get_user_confirmation(f"Try alternative name '{alternative_name}'?"):
                        try:
                            alternative_path = file_path.parent / alternative_name
                            file_path.rename(alternative_path)
                            files_renamed += 1
                            print(f"  Successfully renamed to: {alternative_name}")
                        except Exception as e:
                            print(f"  Error with alternative name: {e}")
                    continue
                
                try:
                    file_path.rename(new_path)
                    files_renamed += 1
                except Exception as e:
                    print(f"  Error renaming '{old_name}': {e}")
                    
                    # If it's a file exists error, offer alternative naming
                    if "exists" in str(e).lower() or "cannot create" in str(e).lower():
                        alternative_name = get_alternative_filename(file_path, new_name)
                        if get_user_confirmation(f"Try alternative name '{alternative_name}'?"):
                            try:
                                alternative_path = file_path.parent / alternative_name
                                file_path.rename(alternative_path)
                                files_renamed += 1
                                print(f"  Successfully renamed to: {alternative_name}")
                            except Exception as e2:
                                print(f"  Error with alternative name: {e2}")
            else:
                # In dry-run mode, count the file unless target exists
                if not new_path.exists():
                    files_renamed += 1
                elif verbose:
                    print(f"  Warning: '{new_name}' already exists. Would skip.")
                    # Suggest alternative filename in dry-run mode
                    alternative_name = get_alternative_filename(file_path, new_name)
                    print(f"  Alternative name would be: '{alternative_name}'")
                    # Count this as a file that could be renamed (with alternative name)
                    files_renamed += 1
    
    if verbose:
        if dry_run:
            print(f"Dry run complete. {files_renamed} files would be renamed.")
            if files_renamed > 0:
                if get_user_confirmation("Proceed with renaming these files?"):
                    # Recursively call with wet run
                    rename_files(path, recursive, dry_run=False, verbose=verbose, first_call=False)
        else:
            print(f"Complete. {files_renamed} files renamed.")

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