# File Renamer

Rename files with Windows-friendly names from Windows CMD, WSL, Linux, or macOS.
Requires **Python 3.9 or newer**. The app and tests use only the Python standard
library. There is no platform-specific compilation or runtime dependency.

## Install or run from the checkout

Install into your Python environment to get a `filerenamer` command on PATH:

```bash
# WSL/Linux/macOS (a virtual environment is recommended)
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install .
filerenamer --help
```

```cmd
REM Windows CMD
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install .
filerenamer --help
```

You can also run without installing or building:

```bash
python3 filerenamer.py --help
# WSL/Linux/macOS launcher
sh ./filerenamer --help
```

```cmd
py -3 filerenamer.py --help
filerenamer.bat --help
```

The launchers find `filerenamer.py` beside themselves and work from any current
directory, including paths with spaces. Keep the launcher and Python script
together when moving them; add their directory to PATH for system-wide use.
On WSL/Linux/macOS, run `chmod +x filerenamer` to invoke the shell launcher
directly. The CMD launcher tries `py -3`, `python`, then `python3`, checking for
Python 3.9+. It preserves errors and exit status and does not pause.

## Usage

```text
filerenamer [-h] [--version] [-r] [-w | -n] [-q] [--camelcase] [PATH ...]
```

| Option | Behavior |
| --- | --- |
| `PATH ...` | One or more files, directories, or wildcard patterns; defaults to the current directory |
| `-h`, `--help` | Show options, naming rules, and examples |
| `--version` | Print the recorded local build time as `yyyy-mm-dd_hh-mm-ss` and exit |
| `--camelcase` | Join filename words in CamelCase, removing spaces and punctuation |
| `-w`, `--wet` | Apply renames immediately, without asking for confirmation |
| `-n`, `--dry-run` | Preview only; do not prompt or rename |
| `-r`, `--recursive` | Include subdirectories and enable recursive `**` patterns |
| `-q`, `--quiet` | Show errors only, without prompting; combine with `-w` to rename |

By default, the program proposes names and asks whether to proceed:

```text
filerenamer "my file.txt"
Proposed: my file.txt -> my-file.txt
Preview complete. 1 files would be renamed.
Proceed with renaming these files? (Y/n):
```

Press **Enter**, **y**, or **Y** to apply the proposed renames. Any other input
cancels and exits without renaming, including `n` or `yes`. Closed input (EOF)
and Ctrl+C at the prompt also cancel. There is one confirmation for the whole
selection, including multiple paths or wildcard matches.

Examples work in both WSL shells and Windows CMD:

```text
filerenamer
filerenamer --version
filerenamer "*.txt"
filerenamer --camelcase "*.txt"
filerenamer --dry-run --camelcase "*.txt"
filerenamer -w --camelcase "*.txt" "*.pdf"
filerenamer -w --camelcase "My File.txt" "Another File.pdf"
filerenamer -w -r "path to directory"
filerenamer -r --camelcase "**/*.txt"
filerenamer -w --camelcase -- "-my file.txt"
```

**Quote wildcard patterns** for consistent behavior across shells. The app
expands `*`, `?`, and bracket patterns such as `[abc]`. It also accepts multiple
paths produced when a WSL shell expands an unquoted pattern. Use the path syntax
of the environment running Python (`/mnt/c/...` in WSL, `C:\...` in CMD).
An existing literal filename takes priority over interpreting its wildcard
characters. Overlapping selections process each file once. Unmatched patterns
report an error and never fall back to processing the current directory.

Patterns follow Python glob rules: `*` alone does not select dotfiles; use `.*`
or an explicit filename to select them. A directory argument includes its
immediate files, including dotfiles; `-r` includes nested files. Directories
themselves are never renamed.

## Naming rules

Default mode replaces spaces/commas with `-` and problematic characters with
`_`, including `: ; ? < > | " ' * / \`, their fullwidth variants, and curly
quotes. Repeated hyphens or underscores are collapsed.

With `--camelcase`, spaces and punctuation (including existing hyphens and
underscores) separate words. The first letter of each word is capitalized and
the words are joined without inserting separators. Existing capitals, Unicode
letters, numbers, and combining accents are preserved.

| Original | Default | `--camelcase` |
| --- | --- | --- |
| `my file.txt` | `my-file.txt` | `MyFile.txt` |
| `my file: name.txt` | `my-file_-name.txt` | `MyFileName.txt` |
| `my-file_name.TXT` | `my-file_name.TXT` | `MyFileName.TXT` |
| `my archive.tar.gz` | `my-archive.tar.gz` | `MyArchive.tar.gz` |
| `café notes.txt` | `café-notes.txt` | `CaféNotes.txt` |

The first dot after any leading dot starts the extension chain. CamelCase keeps
extension case and dots (e.g. `.tar.gz`) while removing punctuation/spaces
within each extension. A leading dot is preserved for hidden files. If no name
characters remain, the name becomes `File`. Trailing dots are removed; control
characters are removed in CamelCase mode or replaced in default mode. Windows
device names such as `CON.txt` become `CONFile.txt` in CamelCase mode and
`_CON.txt` in default mode.

## Preview, conflicts, and errors

The default flow previews names and asks for confirmation; `-w` applies changes
immediately. Use `-n`/`--dry-run` to preview without prompting or changing files.
Quiet mode does not prompt or rename unless `-w` is also supplied. Only the
proposals shown before confirmation are applied; new wildcard matches that
appear while waiting are not included.

Files are renamed in place and their contents are unchanged. Existing
destinations and conflicting proposed names are skipped with an error; the app
does not prompt for numbered alternative names. Destinations are checked again
after confirmation. Errors do not stop processing other selected files.

Exit status is `0` for success (including previews and cancellation), `1` for missing paths,
unmatched patterns, conflicts, or file operation errors, and `2` for invalid
command-line usage. Filesystem permissions and filesystem path-length limits
still apply.

## Build version

`--version` prints only the build timestamp and exits successfully, without
prompting, scanning paths, or renaming files:

```text
filerenamer --version
2026-10-05_23-07-09
```

The format is **`yyyy-mm-dd_hh-mm-ss`**, with zero-padded fields and a **24-hour
clock** (`00` through `23`). The example above represents 11:07:09 PM. The
timestamp uses the **current local time of the host performing the build**,
with no UTC or other timezone conversion. It is embedded in the application
and stays fixed when the program runs later, even on a different host or in a
different timezone. It is the build time, not the current run time or the
file's modification time.

`python3 build.py` (WSL/Linux/macOS) or `py -3 build.py` (CMD) records a new
timestamp in `filerenamer.py` before testing and uses that same timestamp in
the wheel. Running from the checkout reports that embedded timestamp from the
last `build.py` run. Direct `pip install .` and `pip wheel .` builds also stamp
their packaged copy with the build host's local time, without changing the
checkout's timestamp. Installing an existing wheel preserves its build time.

The option also works through `python3 filerenamer.py --version`,
`py -3 filerenamer.py --version`, either launcher, and
`python -m filerenamer --version` after installation.

## Test and build

Run the portable build from the repository directory:

```bash
# WSL/Linux/macOS
python3 build.py
```

```cmd
REM Windows CMD
py -3 build.py
```

The build records the host's local build time, **runs all unit, CLI, and
applicable native launcher tests**, stops if any fail, and then uses pip to build
`dist/filerenamer-1.0.0-py3-none-any.whl`. Pip installs the build dependencies
(`setuptools>=61` and `wheel`) in an isolated build environment. For offline
builds with those dependencies already installed, use:

```bash
python3 build.py --no-build-isolation
```

The build also checks that the wheel embeds the same timestamp as the tested
source script.

Run tests without build dependencies:

```bash
python3 -m unittest discover -s tests -v
```

Install a built wheel with
`python3 -m pip install dist/filerenamer-1.0.0-py3-none-any.whl` (use `py -3` in
CMD). `python -m filerenamer` is also available after installation.

GitHub Actions runs tests and builds on Linux, Windows, and macOS with Python
3.9 and 3.14. It also installs the wheel and checks the installed CLI outside the
checkout. Tests cover quoted and shell-expanded globs, multiple paths,
recursive selection, literal bracket filenames, unmatched patterns, CamelCase
and Unicode, Windows-invalid characters and device names, extension handling,
confirmation (Enter/y/Y), cancellation, closed input, explicit dry runs,
conflicts before and after confirmation, help, quiet output, error exit codes,
and relocated launchers. Build-version tests check local host time, zero-padded
24-hour formatting, replacement on rebuild, stable output across runtime
timezone/file-time changes, and version output without file changes. The
installed-wheel checks verify both the console and module entry points.
Native CMD tests run on Windows; POSIX launcher tests run on Linux and macOS.
