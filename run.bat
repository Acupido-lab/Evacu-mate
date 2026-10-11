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
echo Starting EvacuMate Permanent Public Online Runtime Gateway...
echo Public URL: https://extended-unshackle-evoke.ngrok-free.dev
"%UV_EXE%" run gateway.py
goto END

:USE_PYTHON
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat 2>nul
)
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Installing / verifying dependencies...
    python -m pip install -r requirements.txt
)
echo.
echo Starting EvacuMate Permanent Public Online Runtime Gateway...
echo Public URL: https://extended-unshackle-evoke.ngrok-free.dev
python gateway.py
goto END

:END
pause


