@echo off
setlocal

set "ROOT=%~dp0"

echo Restarting backend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\restart-backend.ps1"

echo Restarting frontend...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\restart-frontend.ps1"

echo.
echo Done. Backend and frontend are starting in new PowerShell windows.
exit /b 0
