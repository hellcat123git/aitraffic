"""
mock_demo.py — AI-Traffic: Static Mock Demo

Demonstrates the YOLO detection and adaptive logic flow using static frames 
or just simulated inputs to show how the system thinks.
"""

import time
import numpy as np
import cv2
from src.core.detection_engine import DetectionEngine
from src.core.traffic_logic import TrafficLogic
from src.core.eco_tracker import EcoTracker

def create_mock_frame(road_name, vehicle_count, emergency=False):
    """Creates a dummy BGR frame with text representing traffic."""
    frame = np.zeros((300, 500, 3), dtype=np.uint8)
    color = (0, 0, 255) if emergency else (200, 200, 200)
    cv2.putText(frame, f"ROAD: {road_name}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"VEHICLES: {vehicle_count}", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    if emergency:
        cv2.putText(frame, "!!! EMERGENCY !!!", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return frame

def main():
    print("🚦 AI-Traffic: Static Logic Demo 🚦")
    print("This demo simulates the system's thinking process without requiring cameras or SUMO.")
    
    logic = TrafficLogic(min_green=5, max_green=10)
    eco = EcoTracker()
    
    # Simulated Scenario: Road 1 has 2 cars, Road 2 has 8 cars
    scenarios = [
        {"r1": 2, "r2": 8, "e1": 0, "e2": 0, "desc": "Road 2 has more traffic, system should prepare to switch."},
        {"r1": 2, "r2": 8, "e1": 0, "e2": 1, "desc": "EMERGENCY on Road 2! Immediate priority shift."},
        {"r1": 10, "r2": 2, "e1": 0, "e2": 0, "desc": "Normal adaptive flow: Road 1 now busy."}
    ]

    for i, scen in enumerate(scenarios):
        print(f"\n--- Scenario {i+1}: {scen['desc']} ---")
        
        # 1. Update logic with simulated data
        logic.update_road_stats(1, scen['r1'], scen['e1'])
        logic.update_road_stats(2, scen['r2'], scen['e2'])
        
        # 2. Run decision cycle for a few 'seconds'
        for sec in range(8):
            decision = logic.decide()
            signals = logic.get_signal_states()
            
            s1 = signals.get(1, "RED")
            s2 = signals.get(2, "RED")
            
            print(f"Time {sec}s | R1: {scen['r1']} ({s1}) | R2: {scen['r2']} ({s2}) | Action: {decision}")
            
            if decision == "SWITCH_COMPLETE":
                 eco.calculate_savings(scen['r1'] if logic.current_road==2 else scen['r2'], logic.max_green)
            
            time.sleep(0.5) # Speed up demo

    print("\n" + "="*40)
    print(f"Demo Complete. CO2 Saved (Heuristic): {eco.get_total_saved()} kg")
    print("="*40)

if __name__ == "__main__":
    main()
