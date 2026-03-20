# 🚦 AI-Traffic: The Smart City Orchestrator

**Hackathon Edition: Redefining Urban Mobility with AI & Sustainability.**

AI-Traffic is not just a traffic light timer; it's a **Cognitive City Brain** that optimizes for life-saving speed, carbon neutrality, and human-centric safety.

## 🚀 Why This Wins
Current systems are static or reactive. **AI-Traffic is proactive.**
1. **The Guardian (Safety First):** Detects Ambulances/Fire Trucks using computer vision and forces a "Green Flush" for the emergency lane.
2. **The Eco-Optimizer:** Reduces idling time, directly calculating and displaying CO2 savings in real-time.
3. **The Cognitive Warden:** An LLM-powered (Gemini) interface that allows city officials to talk to their infrastructure.

## 🛠️ Key Features
- **YOLOv8 CV Engine:** Real-time multi-vehicle and pedestrian detection.
- **Adaptive Priority Logic:** Dynamic signal timing that shifts green time to where it's needed most.
- **V2X Simulation:** Simulation mode for hardware-free testing and demonstrations.
- **Live Dashboards:** Professional-grade UI built with Streamlit and FastAPI.
- **Hardware Ready:** Seamless integration with Arduino/ESP32 for physical signal control.

## 🏗️ Project Structure
```text
src/
├── core/
│   ├── detection_engine.py # YOLOv8 & Emergency Logic
│   ├── traffic_logic.py    # Priority-based switching
│   └── eco_tracker.py      # CO2 Analytics
├── comm/
│   ├── arduino_bridge.py   # Serial/Simulation Comm
│   └── api_server.py       # FastAPI Data Hub
├── ui/
│   └── dashboard.py        # Streamlit Smart City App
└── utils/
    └── gemini_helper.py    # LLM Warden Interface
```

## 🚥 Quick Start
1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the API Server:**
   ```bash
   python src/comm/api_server.py
   ```
3. **Run the AI Engine:**
   ```bash
   python main_app.py --sim
   ```
4. **Launch the Dashboard:**
   ```bash
   streamlit run src/ui/dashboard.py
   ```

## 🌍 The Mission
To reduce global urban emissions by 15% and emergency response times by 30% using localized, cost-effective AI edge solutions.
