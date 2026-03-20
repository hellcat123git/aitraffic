@echo off
title AI-Traffic: Smart City Orchestrator
color 0B

echo ======================================================
echo   🚦 AI-Traffic: Smart City Orchestrator 🚦
echo ======================================================
echo.

:: 1. KILL GHOST PROCESSES (Fixes Port 8000 error)
echo [0/2] Cleaning up old sessions...
taskkill /f /im python.exe /t >nul 2>&1

echo [1/2] Checking and Installing Dependencies...
python -m pip install -r requirements.txt --no-warn-script-location

echo.
echo [2/2] Launching the Smart City System...
echo.

python run_smart_city.py

echo.
echo ======================================================
echo   🛑 System Finished. Press any key to close.
echo ======================================================
pause
