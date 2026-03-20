import cv2
import time
import argparse
import threading
import requests
from src.core.detection_engine import DetectionEngine
from src.core.traffic_logic import TrafficLogic
from src.core.eco_tracker import EcoTracker
from src.comm.arduino_bridge import ArduinoBridge

API_UPDATE_URL = "http://localhost:8000/update"

def push_to_api(data):
    try:
        requests.post(API_UPDATE_URL, json=data, timeout=0.1)
    except:
        pass # Server might not be running

def main():
    parser = argparse.ArgumentParser(description="AI Traffic System - Hackathon Edition")
    parser.add_argument("--cam1", type=int, default=0, help="Camera index for Road 1")
    parser.add_argument("--cam2", type=int, default=1, help="Camera index for Road 2")
    parser.add_argument("--port", type=str, default=None, help="Serial port for Arduino")
    parser.add_argument("--sim", action="store_true", help="Force simulation mode (no hardware)")
    args = parser.parse_args()

    # Initialize Modules
    print("[INIT] Loading AI Models...")
    detector = DetectionEngine()
    logic = TrafficLogic()
    eco = EcoTracker()
    arduino = ArduinoBridge(port=None if args.sim else args.port)

    # Video Sources
    single_cam = (args.cam1 == args.cam2)
    cap1 = cv2.VideoCapture(args.cam1)
    cap2 = None if single_cam else cv2.VideoCapture(args.cam2)

    if not cap1.isOpened():
        print(f"[ERROR] Could not open Camera {args.cam1}")
        return

    # State
    prev_signals = (None, None)
    
    print("[RUN] System Active. Press 'q' to exit.")

    try:
        while True:
            ret1, frame1 = cap1.read()
            if single_cam:
                ret2, frame2 = True, frame1.copy() if ret1 else None
            else:
                ret2, frame2 = cap2.read()
            
            if not ret1 or not ret2:
                print("[ERROR] Camera feed lost. Retrying...")
                time.sleep(1)
                continue

            # 1. Detect
            counts1, processed1 = detector.detect(frame1)
            counts2, processed2 = detector.detect(frame2)

            # 2. Update Logic
            # DetectionEngine.detect returns a dict where "car", "bus", etc. are separate.
            # Total count:
            total1 = counts1["car"] + counts1["motorcycle"] + counts1["bus"] + counts1["truck"]
            total2 = counts2["car"] + counts2["motorcycle"] + counts2["bus"] + counts2["truck"]
            logic.update_road_stats(1, total1, counts1["emergency"])
            logic.update_road_stats(2, total2, counts2["emergency"])

            # 3. Decision
            decision = logic.decide()
            s1, s2 = logic.get_signal_states()

            # 4. Communicate to Arduino
            if (s1, s2) != prev_signals:
                arduino.send(f"R1_{s1}")
                arduino.send(f"R2_{s2}")
                prev_signals = (s1, s2)
                
                # Update Eco Tracker if a switch occurred
                # We assume a switch happens when a road has finished its green cycle
                if decision == "SWITCH_COMPLETE":
                    # Current road is the one that JUST turned green
                    # Previous road was the one waiting.
                    other_road = 1 if logic.current_road == 2 else 2
                    other_count = total1 if other_road == 1 else total2
                    eco.calculate_savings(other_count, logic.max_green) # Rough estimate

            # 5. UI Overlay
            # Road 1
            cv2.putText(processed1, f"Road 1: {total1} vehicles", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(processed1, f"Signal: {s1}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if s1=="GREEN" else (0,0,255), 2)
            if counts1["emergency"] > 0:
                cv2.putText(processed1, "!!! EMERGENCY !!!", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # Road 2
            cv2.putText(processed2, f"Road 2: {total2} vehicles", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(processed2, f"Signal: {s2}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if s2=="GREEN" else (0,0,255), 2)
            if counts2["emergency"] > 0:
                cv2.putText(processed2, "!!! EMERGENCY !!!", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            # 6. Push to Dashboard API
            api_data = {
                "road1_count": total1,
                "road2_count": total2,
                "road1_signal": s1,
                "road2_signal": s2,
                "road1_emergency": counts1["emergency"],
                "road2_emergency": counts2["emergency"],
                "total_co2_saved": float(eco.get_total_saved())
            }
            push_to_api(api_data)
            print(f"[LIVE] R1:{total1} ({s1}) | R2:{total2} ({s2}) | CO2:{eco.get_total_saved()}kg", end="\r")

            # Dashboard Info
            combined = cv2.vconcat([processed1, processed2])
            cv2.putText(combined, f"Total CO2 Saved: {eco.get_total_saved()} kg", (10, combined.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            cv2.imshow("AI Traffic Control System - Hybrid Edition", combined)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap1.release()
        cap2.release()
        cv2.destroyAllWindows()
        arduino.send("ALL_RED")
        arduino.close()
        print(f"[EXIT] Total CO2 Saved: {eco.get_total_saved()} kg")

if __name__ == "__main__":
    main()
