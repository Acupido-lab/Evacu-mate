@echo off
title EvacuMate - Permanent Public Online Runtime Gateway
cd /d "%~dp0"

echo ===============================================================
echo     EvacuMate Permanent Public Online Runtime Gateway
echo ===============================================================
echo.

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" gateway.py
if errorlevel 1 (
    echo.
    echo ===============================================================
    echo Gateway stopped. Check gateway_config.json or gateway.log.
    echo ===============================================================
    pause
)
