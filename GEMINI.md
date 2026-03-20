# GEMINI.md - AI-Traffic: Smart City Orchestrator

This file serves as the core instructional context for the **AI-Traffic** project, an advanced, modular AI system designed for real-time urban traffic management and optimization.

## 🚀 Project Overview
**AI-Traffic** is a "Smart City Brain" developed for high-impact hackathon demonstrations. It goes beyond simple vehicle counting by integrating safety, sustainability, and generative AI into a single orchestrated platform.

### Core Technologies
- **Computer Vision:** YOLOv8 (ultralytics) for real-time object detection.
- **Backend:** FastAPI for high-performance asynchronous data handling.
- **Frontend:** Streamlit for a polished, interactive "Digital Twin" dashboard.
- **Intelligence:** Google Gemini API for the "AI Traffic Warden" natural language interface.
- **Hardware:** Serial communication with Arduino/ESP32 (with built-in simulation mode).

### Architecture
- `main_app.py`: The central orchestrator connecting vision, logic, and hardware.
- `src/core/`: The "Brain" containing detection heuristics, adaptive traffic signal logic, and CO2 analytics.
- `src/comm/`: The "Nervous System" handling internal API state and external hardware communication.
- `src/ui/`: The "Face" of the project providing real-time visualization and analytics.
- `src/utils/`: Support modules for LLM integration and helper functions.

---

## 🛠 Building and Running

### Prerequisites
- **Python 3.12 (Recommended):** Use the stable 3.12 release to ensure library compatibility.
- **Dependencies:** Install via `pip install -r requirements.txt`.

### Key Commands
- **Master Launch:** `python run_smart_city.py` (Launches API, AI Engine, and Dashboard).
- **Windows Launcher:** Double-click `launch_smart_city.bat`.
- **Individual Components:**
    - API Server: `python src/comm/api_server.py`
    - AI Engine: `python main_app.py --sim`
    - Dashboard: `streamlit run src/ui/dashboard.py`

---

## 🚥 Key Features (Implemented)
1. **The Guardian (Safety):** Immediate signal preemption for emergency vehicles (Ambulances/Fire Trucks) detected via CV.
2. **The Eco-Optimizer (Sustainability):** Real-time CO2 savings calculator based on reduced idling time.
3. **The Cognitive Warden (LLM):** A Gemini-powered chat interface in the dashboard for querying city-wide traffic stats.
4. **Hardware-Agnostic:** Seamlessly switches between physical Arduino control and software simulation.

---

## 📝 Development Conventions
- **Modular Design:** Logic must be kept in `src/core/`. UI must not contain business logic; it should pull from the FastAPI `/data` endpoint.
- **Simulation Mode:** Always provide a `--sim` or fallback path for hardware components to ensure the system is "demo-ready" in any environment.
- **Safety Heuristics:** Emergency detection currently uses color-based heuristics (Red on heavy vehicles) for the demo, allowing for easy visual "wow" moments.

---

## 🔮 Future Roadmap (TODO)
- [ ] **Wrong-Way Detection:** Implement vector tracking to identify vehicles driving against traffic flow.
- [ ] **Automatic Fining System:** Capture snapshots of red-light violations and generate mock "Smart Challans."
- [ ] **Digital Twin UI:** Upgrade Streamlit with isometric 3D maps or Three.js integrations.
