"""
main_app.py — AI-Traffic: Unified Smart City Orchestrator

This is the central entry point for both real-world video detection (YOLOv8)
and high-fidelity simulation (SUMO).

Usage:
  # Video/YOLO Mode
  python main_app.py --mode yolo --cam1 0 --cam2 1

  # SUMO Simulation Mode (AI-Driven)
  python main_app.py --mode sumo

  # SUMO Simulation Mode (Baseline/Fixed-Time)
  python main_app.py --mode sumo --baseline
"""

import time
import argparse
import sys
import os
import cv2

# Core Modules
from src.core.detection_engine import DetectionEngine
from src.core.sumo_engine import SumoEngine
from src.core.traffic_logic import TrafficLogic
from src.core.eco_tracker import EcoTracker


def run_yolo_mode(args):
    """Real-time camera/video detection mode."""
    print("[INIT] Loading YOLOv8 Detection Engine...")
    detector = DetectionEngine()
    logic = TrafficLogic()
    eco = EcoTracker()

    def open_source(src):
        try:
            return cv2.VideoCapture(int(src))
        except ValueError:
            return cv2.VideoCapture(src)

    single_cam = (args.cam1 == args.cam2)
    cap1 = open_source(args.cam1)
    cap2 = None if single_cam else open_source(args.cam2)

    if not cap1.isOpened():
        print(f"[ERROR] Could not open Source {args.cam1}")
        return

    # Register roads (2-way intersection for YOLO demo)
    logic.update_road_stats(1, 0)
    logic.update_road_stats(2, 0)

    print("[RUN] YOLO Mode Active. Press 'q' to exit.")

    try:
        while True:
            ret1, frame1 = cap1.read()
            if single_cam:
                ret2, frame2 = True, frame1.copy() if ret1 else None
            else:
                ret2, frame2 = cap2.read()
            
            if not ret1 or not (ret2 if cap2 else True):
                time.sleep(1)
                continue

            # 1. Detect
            counts1, processed1 = detector.detect(frame1)
            counts2, processed2 = (counts1, processed1) if single_cam else detector.detect(frame2)

            # 2. Update Logic
            total1 = counts1.get("total", 0)
            total2 = counts2.get("total", 0)
            logic.update_road_stats(1, total1, counts1.get("emergency", 0))
            logic.update_road_stats(2, total2, counts2.get("emergency", 0))

            # 3. Decision
            decision = logic.decide()
            signals = logic.get_signal_states()
            s1, s2 = signals.get(1, "RED"), signals.get(2, "RED")

            # 4. Eco Tracking
            if decision == "SWITCH_COMPLETE":
                other_road = 1 if logic.current_road == 2 else 2
                other_count = total1 if other_road == 1 else total2
                eco.calculate_savings(other_count, logic.max_green)

            # 5. UI Overlay
            cv2.putText(processed1, f"R1: {total1} ({s1})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(processed2, f"R2: {total2} ({s2})", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            
            combined = cv2.vconcat([processed1, processed2])
            cv2.imshow("AI-Traffic: YOLO Mode", combined)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap1.release()
        if cap2: cap2.release()
        cv2.destroyAllWindows()


def run_sumo_mode(args):
    """High-fidelity simulation mode."""
    print(f"[INIT] Starting SUMO Engine (Baseline={args.baseline})...")
    
    logic = TrafficLogic()
    eco = EcoTracker()
    eco.set_sumo_mode("sumo_baseline" if args.baseline else "sumo_ai")

    try:
        engine = SumoEngine(
            config="sumo/intersection.sumocfg",
            gui=args.gui,
            baseline=args.baseline,
            port=args.port,
            metrics_output="sumo/output/live_metrics.json"
        )
        engine.set_logic(logic)
    except Exception as e:
        print(f"\n[ERROR] SUMO failed: {e}")
        return

    print(f"[RUN] SUMO Interface Active. Mode: {'Baseline' if args.baseline else 'AI-Optimized'}")

    try:
        while True:
            # 1. Advance simulation & get vehicle counts
            counts, _ = engine.detect()
            if not counts: break

            # 2. Update logic for all 4 approaches
            for road in ['north', 'south', 'east', 'west']:
                is_evp = (road == engine._evp_approaching_road) if hasattr(engine, '_evp_approaching_road') else False
                logic.update_road_stats(road, counts.get(road, 0), counts.get("emergency", 0) if is_evp else 0)

            # 3. Decision & Signal Override (if AI mode)
            if not args.baseline:
                logic.decide()
                phase_string = logic.get_traci_phase_string()
                engine.apply_signal(phase_string)

            # 4. Metrics & Eco tracking
            metrics = engine.get_metrics()
            eco.ingest_traci_metrics(metrics["co2_mg"], metrics["avg_wait_s"])

            if engine._step % 50 == 0:
                print(f"Step: {engine._step} | Vehicles: {metrics['vehicle_count']} | Wait: {metrics['avg_wait_s']}s", end="\r")

            # 5. Inject Emergency Event
            if engine._step == 300:
                print("\n[EVENT] Injecting Emergency Vehicle...")
                engine.inject_emergency()

    except KeyboardInterrupt:
        print("\n[STOP] Simulation stopped by user.")
    finally:
        engine.release()
        report = eco.get_benchmark_report()
        print("\n" + "="*40)
        print("  Simulation Results")
        print(f"  Mode: {'Baseline' if args.baseline else 'AI'}")
        print(f"  Avg Wait Time: {metrics['avg_wait_s']:.2f}s")
        print(f"  Total CO2: {metrics['co2_mg']:.2f}mg")
        print("="*40)


def main():
    parser = argparse.ArgumentParser(description="AI-Traffic Unified Orchestrator")
    parser.add_argument("--mode", type=str, choices=["yolo", "sumo"], default="yolo", help="Mode: yolo or sumo")
    parser.add_argument("--baseline", action="store_true", help="Run SUMO in fixed-time baseline mode")
    parser.add_argument("--gui", action="store_true", default=True, help="Show SUMO GUI")
    parser.add_argument("--no-gui", action="store_false", dest="gui", help="Hide SUMO GUI")
    parser.add_argument("--port", type=int, default=8813, help="TraCI port for SUMO")
    
    # YOLO args
    parser.add_argument("--cam1", type=str, default="0")
    parser.add_argument("--cam2", type=str, default="1")
    
    args = parser.parse_args()

    if args.mode == "yolo":
        run_yolo_mode(args)
    else:
        run_sumo_mode(args)


if __name__ == "__main__":
    main()
