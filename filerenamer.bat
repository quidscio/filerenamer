@echo off
setlocal
REM Select Python 3 before running the app so an app error never reruns renames.
py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto :py
python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto :python
python3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1
if not errorlevel 1 goto :python3
echo ERROR: Python 3.9 or newer is required. Install Python and add it to PATH. 1>&2
exit /b 1

:py
py -3 "%~dp0filerenamer.py" %*
exit /b %errorlevel%

:python
python "%~dp0filerenamer.py" %*
exit /b %errorlevel%

:python3
python3 "%~dp0filerenamer.py" %*
exit /b %errorlevel%
