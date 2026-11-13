@echo off
REM Double-click this file to start Vehicle Tinder (Windows).
REM Keep this file inside the "Vehicle tinder" folder.

cd /d "%~dp0"

where python >nul 2>&1
if %ERRORLEVEL%==0 (
  set PYTHON_BIN=python
  goto run
)

where python3 >nul 2>&1
if %ERRORLEVEL%==0 (
  set PYTHON_BIN=python3
  goto run
)

echo.
echo Python 3 was not found.
echo Install it from https://www.python.org/downloads/
echo During setup, enable "Add Python to PATH", then try again.
echo.
pause
exit /b 1

:run
echo Starting Vehicle Tinder with: %PYTHON_BIN%
echo A browser window should open shortly.
echo Leave this window open while you label. Close it or press Ctrl+C to stop.
echo.
%PYTHON_BIN% app.py
if errorlevel 1 (
  echo.
  echo The app exited with an error.
  pause
)
