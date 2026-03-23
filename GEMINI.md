# GEMINI.md - Foundational Mandates & Project Blueprint

> [!IMPORTANT]
> **Session Handover:** Upon starting a new chat, you MUST first read this file (`GEMINI.md`) for architectural mandates, followed immediately by `context/continuation.md` to synchronize with the latest project progress, completed tasks, and pending roadmap items.

## Project Overview: AI-Traffic Smart City Orchestrator
AI-Traffic is a modular, AI-driven traffic management system designed to optimize urban mobility, reduce CO2 emissions, and provide life-saving Emergency Vehicle Preemption (EVP). It bridges the gap between high-fidelity simulation (SUMO) and real-world edge execution (YOLOv8 + ESP32).

---

## 🏗️ Architectural Blueprint

### 1. Sensing & Detection Layer (`src/core/`)
- **`DetectionEngine` (YOLOv8)**: Real-time multi-vehicle/pedestrian counting from camera feeds. Features a unique HSV-based red-dominance heuristic for emergency vehicle detection on non-custom-trained models.
- **`SumoEngine` (TraCI)**: High-fidelity simulation interface. Provides milligram-level CO2 tracking, proximity-based EVP sensors, and ground-truth wait-time metrics.
- **`BaseEngine`**: The critical abstract interface ensuring `DetectionEngine` and `SumoEngine` are 100% hot-swappable.

### 2. Logic & Decision Layer (`src/core/traffic_logic.py`)
- **Adaptive Control**: A dynamic state machine implementing the **Indian 4-Phase (Split-Phasing)** standard (IRC:93-1985). It gives each approach (North, East, South, West) a dedicated green interval to handle heterogeneous traffic and safe right turns.
- **Clearance Logic**: Every transition enforces a mandatory **Green -> Yellow -> All-Red** sequence for maximum intersection safety.
- **Priority Green Wave (EVP)**: A safety-first override that grants immediate green lights to emergency vehicles, but strictly enforces a 4-second yellow clearance for cross-traffic to prevent real-world collisions.

### 3. Analytics & Sustainability (`src/core/eco_tracker.py`)
- **Carbon Accounting**: Tracks CO2 savings using both simulation-accurate data (mg) and scientifically robust VSP (Vehicle Specific Power) re-acceleration penalties (e.g., 0.045kg per stop-start).
- **Benchmark Reports**: Generates side-by-side comparison data (AI vs. Baseline) calculating true Mean Delay per Vehicle for validated performance reporting.

### 4. Hardware & UI Layer
- **ESP32 Integration**: Serial communication protocols (`experiments_and_tests/control_esp32.py`) for controlling physical traffic signal hardware, including a 1s 'OK' heartbeat watchdog.
- **Next.js High-End Frontend (`frontend/`)**: A production-grade React 15 dashboard using a GPU-Native (Zustand + deck.gl) pipeline for high-frequency (10Hz+) traffic visualization. Features an Intelligent Bento Grid layout with Glassmorphism.
- **Streamlit Dashboard**: A secondary Python-based dashboard for rapid testing and parallel benchmarking metrics.

---

## 🛠️ Development & Tooling Mandates

### External Tooling: Antigravity IDE (Google)
- **Agent-First Workflows**: Use Antigravity's 'Mission Control' to delegate full-stack optimization tasks.
- **Multi-Surface Execution**: Leverage the integrated Terminal (SUMO), Browser (Streamlit), and Editor to automate closed-loop testing of traffic algorithms.
- **Recommended Skills**: 
  - `computer-vision-expert` (YOLOv8 tuning)
  - `traffic-logic-tester` (SUMO edge-case validation)
  - `embedded-systems-pro` (ESP32/Serial HIL testing)

### Core Coding Standards
- **Interface Integrity**: Always maintain strict adherence to the `BaseEngine` abstract class when adding new sensing modules (e.g., LiDAR, Radar).
- **Surgical Updates**: Prioritize focused, idiomatic changes. Avoid refactoring unrelated logic unless explicitly requested.
- **Validation Protocol**: Every logic change MUST be validated against the `SumoEngine` benchmark before deployment to physical hardware.

### Simulation Commands
- **Build Network**: `python build_sumo_net.py`
- **Run AI-Driven Mode**: `python main_app.py --mode sumo`
- **Run Baseline Mode**: `python main_app.py --mode sumo --baseline`

---

## 🚦 Future Roadmap
1. **Multi-Intersection Coordination**: Implementing "Green Waves" across networked intersections.
2. **V2X Integration**: Incorporating connected vehicle data into the density estimation algorithm.
3. **Advanced Pedestrian Safety**: Expanding logic to handle dedicated pedestrian phases based on dynamic crosswalk demand.
