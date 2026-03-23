"""
run_smart_city.py — AI-Traffic: Smart City Orchestrator

Integrates SumoEngine with TrafficLogic and EcoTracker to demonstrate 
the full-stack traffic management system in a simulation environment.
"""

import time
import argparse
import os

from src.core.sumo_engine import SumoEngine
from src.core.traffic_logic import TrafficLogic
from src.core.eco_tracker import EcoTracker

def main():
    parser = argparse.ArgumentParser(description="AI-Traffic: Smart City simulation mode")
    parser.add_argument("--gui", action="store_true", default=True, help="Run with SUMO-GUI")
    parser.add_argument("--no-gui", action="store_false", dest="gui", help="Run in headless mode")
    parser.add_argument("--baseline", action="store_true", help="Run fixed-time baseline simulation")
    parser.add_argument("--metrics", type=str, default="sumo/output/live_metrics.json", help="Path for live metrics JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("  🚦 AI-Traffic: Smart City Orchestrator")
    print("  Mode: " + ("BASELINE (Fixed)" if args.baseline else "AI-OPTIMIZED (Adaptive)"))
    print("=" * 60)

    # 1. Initialize Logic & Tracker
    logic = TrafficLogic()
    eco = EcoTracker()
    eco.set_sumo_mode("sumo_baseline" if args.baseline else "sumo_ai")

    # 2. Start Sumo Engine
    try:
        engine = SumoEngine(
            config="sumo/intersection.sumocfg",
            gui=args.gui,
            baseline=args.baseline,
            metrics_output=args.metrics
        )
        engine.set_logic(logic)
    except Exception as e:
        print(f"\n❌ ERROR starting SUMO: {e}")
        print("   Make sure SUMO is installed and SUMO_HOME is set.")
        return

    print("\n🚀 Simulation active. Close SUMO-GUI to end.")

    try:
        while True:
            # A. Detect (Step Simulation)
            counts, _ = engine.detect()
            if not counts or counts.get("total", 0) == 0 and engine._step > 500: # Simple exit condition if empty
                # Check if simulation is still running
                try:
                    import traci
                    if not traci.simulation.getMinExpectedNumber() > 0:
                        break
                except:
                    break

            # B. Update Logic Stats
            # SUMO mode uses 'north', 'south', 'east', 'west' keys
            for road in ['north', 'south', 'east', 'west']:
                logic.update_road_stats(road, counts.get(road, 0), counts.get("emergency", 0) if road == engine._evp_approaching_road else 0)

            # C. Decision (if not baseline)
            if not args.baseline:
                decision = logic.decide()
                phase_string = logic.get_traci_phase_string()
                engine.apply_signal(phase_string)

            # D. Track Metrics
            metrics = engine.get_metrics()
            eco.ingest_traci_metrics(metrics["co2_mg"], metrics["avg_wait_s"])

            # E. Feedback
            if engine._step % 10 == 0:
                s = f"Step: {engine._step} | Vehicles: {metrics['vehicle_count']} | Wait: {metrics['avg_wait_s']:.1f}s | CO2: {metrics['co2_mg']:.0f}mg"
                if metrics["evp_active"]:
                    s += " | 🚑 EVP ACTIVE!"
                print(s, end="\r")

            # F. Optional: Inject Emergency at step 300
            if engine._step == 300:
                print("\n[EVENT] Injecting Emergency Vehicle...")
                engine.inject_emergency()

    except KeyboardInterrupt:
        print("\n[STOP] User interrupted.")
    except Exception as e:
        print(f"\n[ERROR] Simulation error: {e}")
    finally:
        engine.release()
        print("\n" + "=" * 60)
        print("  📊 Session Summary")
        print(f"  Total Steps: {engine._step}")
        if args.baseline:
             print("  Mode: Baseline (Run again without --baseline to compare)")
        else:
             report = eco.get_benchmark_report()
             print(f"  AI CO2: {report['ai_co2_mg']:.1f} mg")
             print(f"  AI Avg Wait: {report['ai_avg_wait_s']:.1f} s")
        print("=" * 60)

if __name__ == "__main__":
    main()
