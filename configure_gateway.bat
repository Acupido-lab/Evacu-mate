@echo off
title EvacuMate Gateway Configuration
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
)

"%PYTHON_EXE%" configure_gateway.py
