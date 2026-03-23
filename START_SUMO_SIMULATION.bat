@echo off
SETLOCAL EnableExtensions
title AI-Traffic: SUMO Interface Orchestrator
color 0A

echo ======================================================
echo   AI-Traffic: SUMO Interface Orchestrator
echo ======================================================
echo.

:: 1. AUTO-DETECT SUMO_HOME
echo [1/5] Searching for SUMO installation...
for /f "delims=" %%i in ('python -c "import os, sumo; print(os.path.dirname(sumo.__file__))" 2^>nul') do set "SUMO_HOME=%%i"

if "%SUMO_HOME%"=="" (
    if exist "C:\Program Files (x86)\Eclipse\Sumo" set "SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo"
    if exist "C:\Program Files\Eclipse\Sumo" set "SUMO_HOME=C:\Program Files\Eclipse\Sumo"
)

if "%SUMO_HOME%"=="" (
    echo [!] SUMO not found. Attempting to install eclipse-sumo...
    python -m pip install eclipse-sumo traci --quiet
    for /f "delims=" %%i in ('python -c "import os, sumo; print(os.path.dirname(sumo.__file__))" 2^>nul') do set "SUMO_HOME=%%i"
)

if "%SUMO_HOME%"=="" (
    echo.
    echo ERROR: SUMO still not found. Please install it manually.
    pause
    exit /b
)

echo Found SUMO at: %SUMO_HOME%
set "PATH=%SUMO_HOME%\bin;%PATH%"

:: 2. CLEANUP
echo [2/5] Cleaning up old sessions...
taskkill /f /im sumo.exe /t >nul 2>&1
taskkill /f /im sumo-gui.exe /t >nul 2>&1

:: 3. BUILD NETWORK
echo [3/5] Building the SUMO Network...
python build_sumo_net.py

:: 4. RUN COMPARISON
echo.
echo [4/5] Launching Side-by-Side Comparison...
echo ------------------------------------------------------
echo  LEFT: Baseline  ^|  RIGHT: AI-Optimized
echo ------------------------------------------------------
echo.

python compare_simulations.py

echo.
echo [5/5] Simulation Finished.
echo Check JUDGES_REPORT.md for metrics.
pause
