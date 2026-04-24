@echo off
setlocal

set "ROOT=%~dp0"
set "VISIBLE_DEBUG="
if /I "%~2"=="--debug" set "VISIBLE_DEBUG=1"

if /I not "%~1"=="--worker" (
  if exist "%ROOT%scripts\run-desktop-hidden.vbs" (
    "%SystemRoot%\System32\wscript.exe" "%ROOT%scripts\run-desktop-hidden.vbs" "%~f0"
    exit /b 0
  )
)

set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo Python not found: %PY%
  echo Please create venv and install backend requirements first.
  exit /b 1
)

pushd "%ROOT%"
if not exist "%ROOT%.runtime\logs" mkdir "%ROOT%.runtime\logs"
set "LOG=%ROOT%.runtime\logs\desktop-launcher.log"
echo [%DATE% %TIME%] Starting Dance Assist desktop...>>"%LOG%"
"%PY%" "%ROOT%desktop_launcher.py" --mode desktop >>"%LOG%" 2>>&1
set "ERR=%ERRORLEVEL%"
popd

if not "%ERR%"=="0" (
  echo Dance Assist failed to start. Error code: %ERR%
  echo Log file: %LOG%
  echo.
  type "%LOG%"
  if "%VISIBLE_DEBUG%"=="1" pause
)

exit /b %ERR%
