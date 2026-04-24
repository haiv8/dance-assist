@echo off
setlocal

call "%~dp0run-desktop.bat" --worker --debug
exit /b %ERRORLEVEL%
