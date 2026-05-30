@echo off
cd /d "%~dp0"
title FRIDAY AI - Personal Terminal Assistant
color 0B

:: Check for virtual environment in different common locations
if exist "d:\FileMind\venv\Scripts\activate.bat" (
    call "d:\FileMind\venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if exist "d:\FileMind\venv\Scripts\python.exe" (
    "d:\FileMind\venv\Scripts\python.exe" main.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
if %ERRORLEVEL% neq 0 (
    echo.
    echo =================================================================
    echo [System Error] FRIDAY AI exited with code %ERRORLEVEL%
    echo =================================================================
    pause
)
