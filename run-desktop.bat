@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Python not found: %PY%
  echo Please create venv and install backend requirements first.
  exit /b 1
)

pushd "%ROOT%"
"%PY%" "%ROOT%desktop_launcher.py" --mode desktop
set "ERR=%ERRORLEVEL%"
popd

exit /b %ERR%
