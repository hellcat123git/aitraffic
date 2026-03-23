@echo off
title AI-Traffic: Smart City V1.0
color 0B

echo ======================================================
echo   🚦 AI-Traffic: V1.0 Production Core 🚦
echo ======================================================
echo.

:: 1. Build Network
echo [1/3] Generating SUMO Network...
python build_sumo_net.py
if %errorlevel% neq 0 (
    echo [ERROR] Network build failed.
    pause
    exit /b %errorlevel%
)

:: 2. Start Simulation in a new window
echo [2/3] Starting AI Simulation Engine (Parallel Benchmark)...
start "AI-Traffic: Sim Engine" python run_benchmark.py --steps 10000

:: 3. Start Dashboard
echo [3/3] Launching Smart City Dashboard...
echo.
streamlit run src/ui/dashboard.py

pause
