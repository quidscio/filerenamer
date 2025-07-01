@echo off
REM Try common Python installation paths
"%USERPROFILE%\anaconda3\python.exe" "C:\q\arc\projects\filerenamer\filerenamer.py" %* 2>nul && goto :success
"%USERPROFILE%\miniconda3\python.exe" "C:\q\arc\projects\filerenamer\filerenamer.py" %* 2>nul && goto :success
"C:\ProgramData\anaconda3\python.exe" "C:\q\arc\projects\filerenamer\filerenamer.py" %* 2>nul && goto :success
"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" "C:\q\arc\projects\filerenamer\filerenamer.py" %* 2>nul && goto :success
py "C:\q\arc\projects\filerenamer\filerenamer.py" %* 2>nul && goto :success

echo ERROR: Python not found in common locations.
echo Please update the batch file with your Python path.
echo.
echo Your Python is likely at one of these locations:
where python 2>nul
echo.

:success
pause