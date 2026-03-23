"""
compare_simulations.py — Side-by-Side SUMO Interface

Launches two parallel SUMO simulations in lockstep:
  - Window 1: BASELINE (Normal fixed-time traffic lights)
  - Window 2: AI-DRIVEN (Adaptive traffic orchestration)

Provides a unified benchmark summary at the end.
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("  🚦 AI-Traffic: Side-by-Side Simulation Comparison")
    print("=" * 60)
    print("  This will launch TWO windows of SUMO-GUI.")
    print("  One for the Baseline (Normal) and one for our AI System.")
    print("=" * 60)
    
    # 1. First, ensure the network is built
    if not os.path.exists("sumo/intersection.net.xml"):
        print("\n🔧 Network not found. Building it now...")
        subprocess.run([sys.executable, "build_sumo_net.py"])

    # 2. Run the benchmark with GUI
    try:
        cmd = [sys.executable, "run_benchmark.py", "--steps", "1000", "--gui"]
        print(f"🚀 Running: {' '.join(cmd)}")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[STOP] Simulation terminated by user.")
    
    print("\n📊 Benchmark finished. Check 'benchmark_report.csv' and 'JUDGES_REPORT.md'.")

if __name__ == "__main__":
    main()
