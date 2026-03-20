@echo off
setlocal

set "ROOT=%~dp0"

echo Restarting backend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\restart-backend.ps1"

echo.
echo Backend is starting in a new PowerShell window.
exit /b 0
