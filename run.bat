@echo off
title EvacuMate Relief ^& Shelter Helper
cd /d "%~dp0"

echo ===================================================
echo     EvacuMate - Relief ^& Shelter Helper Server
echo ===================================================
echo.

set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"

if exist "%UV_EXE%" goto USE_UV
goto USE_PYTHON

:USE_UV
echo Checking virtual environment...
if not exist .venv (
    "%UV_EXE%" venv .venv
)
echo Installing / verifying dependencies...
"%UV_EXE%" pip install -r requirements.txt
echo.
echo Starting EvacuMate server on http://127.0.0.1:8550 ...
"%UV_EXE%" run main.py
goto END

:USE_PYTHON
echo Checking virtual environment...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo Starting EvacuMate server on http://127.0.0.1:8550 ...
python main.py
goto END

:END
pause


