@echo off
setlocal

set "ROOT=%~dp0"

echo Restarting frontend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\restart-frontend.ps1"

echo.
echo Frontend is starting in a new PowerShell window.
exit /b 0
