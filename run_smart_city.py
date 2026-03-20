import subprocess
import time
import sys
import os
import signal

# --- Configuration ---
PYTHON_EXE = sys.executable
API_SERVER_SCRIPT = "src/comm/api_server.py"
AI_ENGINE_SCRIPT = "main_app.py"
DASHBOARD_SCRIPT = "src/ui/dashboard.py"

processes = []

def signal_handler(sig, frame):
    print("\n[SHUTDOWN] Closing AI Traffic System...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def run_system():
    print("🚀 Starting AI-Traffic: Smart City Orchestrator...")
    print("-" * 50)

    # 1. Start API Server
    print("[1/3] Launching Data Hub (FastAPI)...")
    p_api = subprocess.Popen([PYTHON_EXE, API_SERVER_SCRIPT])
    processes.append(p_api)
    time.sleep(2) # Wait for server to bind

    # 2. Start AI Engine (Simulation Mode)
    print("[2/3] Launching Vision Engine (YOLOv8)...")
    # Using --cam1 0 --cam2 0 for default webcam. Change indices if needed.
    p_ai = subprocess.Popen([PYTHON_EXE, AI_ENGINE_SCRIPT, "--sim", "--cam1", "0", "--cam2", "0"])
    processes.append(p_ai)
    time.sleep(3)

    # 3. Start Dashboard
    print("[3/3] Launching Smart Dashboard (Streamlit)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    p_ui = subprocess.Popen(["streamlit", "run", DASHBOARD_SCRIPT], env=env)
    processes.append(p_ui)

    print("-" * 50)
    print("✅ System fully operational!")
    print("👉 Dashboard: http://localhost:8501")
    print("👉 API Docs: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop all components.")
    
    # Keep the script alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    # Check if we are in the right directory
    if not os.path.exists(AI_ENGINE_SCRIPT):
        print(f"Error: Could not find {AI_ENGINE_SCRIPT}. Please run this from the project root.")
    else:
        run_system()
