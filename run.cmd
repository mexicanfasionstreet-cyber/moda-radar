@echo off
setlocal
cd /d "%~dp0"
set "PY=python"
where python >nul 2>nul || set "PY=py -3"
%PY% aggregate.py %*
echo.
if errorlevel 1 pause
