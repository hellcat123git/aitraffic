#!/bin/bash

echo "======================================================"
echo "  🚦 AI-Traffic: V1.0 Production Core 🚦"
echo "======================================================"
echo

# 1. Build Network
echo "[1/3] Generating SUMO Network..."
python3 build_sumo_net.py

# 2. Start Simulation in background
echo "[2/3] Starting AI Simulation Engine (Parallel Benchmark)..."
python3 run_benchmark.py --steps 10000 &
SIM_PID=$!

# 3. Start Dashboard
echo "[3/3] Launching Smart City Dashboard..."
streamlit run src/ui/dashboard.py

# Cleanup simulation on exit
kill $SIM_PID
