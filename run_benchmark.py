"""
run_benchmark.py — AI-Traffic: Parallel Baseline vs AI Benchmark

Runs two SUMO instances concurrently using traci labelled connections
(baseline on port 8813, AI on port 8814), steps them in lockstep for N steps,
collects CO2 + wait-time metrics, and writes:
  - benchmark_report.csv       (step-by-step timeseries)
  - sumo/output/benchmark_summary.json  (final comparison)

Usage:
    python run_benchmark.py [--steps 1000]
    python run_benchmark.py --benchmark  (alias)

SUMO_HOME is auto-detected from eclipse-sumo pip package.
"""

import os
import sys
import csv
import json
import time
import argparse
import subprocess

# ---------------------------------------------------------------------------
# Set SUMO_HOME if eclipse-sumo pip package is present
# ---------------------------------------------------------------------------
def _ensure_sumo_home():
    if os.environ.get("SUMO_HOME"):
        return
    try:
        import sumo as sumo_pkg
        if hasattr(sumo_pkg, "__file__") and sumo_pkg.__file__:
            sumo_home = os.path.dirname(sumo_pkg.__file__)
            os.environ["SUMO_HOME"] = sumo_home
            bin_path = os.path.join(sumo_home, "bin")
            if bin_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
            print(f"[Setup] SUMO_HOME => {sumo_home}")
    except ImportError:
        pass

_ensure_sumo_home()

try:
    import traci
    import traci.constants as tc
except ImportError:
    print("ERROR: traci not installed. Run: pip install traci")
    sys.exit(1)

from src.core.traffic_logic import TrafficLogic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUMO_CFG        = "sumo/intersection.sumocfg"
JUNCTION_ID     = "center"
TLS_ID          = "center"
PROXIMITY_M     = 200.0
EMERGENCY_ROUTE = "west_to_east"
EMERGENCY_TYPE  = "emergency_car"

APPROACH_EDGES = {
    "north": ["north_in"],
    "south": ["south_in"],
    "east":  ["east_in"],
    "west":  ["west_in"],
}

os.makedirs("sumo/output", exist_ok=True)
CSV_PATH   = "benchmark_report.csv"
JSON_PATH  = "sumo/output/benchmark_summary.json"
LIVE_JSON  = "sumo/output/live_metrics.json"


# ---------------------------------------------------------------------------
# Resolve binary path
# ---------------------------------------------------------------------------
def _resolve_binary(name: str) -> str:
    sumo_home = os.environ.get("SUMO_HOME", "")
    if sumo_home:
        for ext in ("", ".exe"):
            cand = os.path.join(sumo_home, "bin", name + ext)
            if os.path.isfile(cand):
                return cand
    return name


# ---------------------------------------------------------------------------
# Launch a SUMO process and return (process, connection) using traci.start
# ---------------------------------------------------------------------------
def _launch_sumo(label: str, port: int, baseline: bool, use_gui: bool = False):
    """Start a SUMO process and connect via traci with a label."""
    binary = _resolve_binary("sumo-gui" if use_gui else "sumo")
    cmd = [
        binary,
        "-c", SUMO_CFG,
        "--no-step-log",
        "--no-warnings",
        "--collision.action", "warn",
        "--time-to-teleport", "300",
        "--remote-port", str(port),
    ]
    if baseline:
        # Use built-in fixed-time TLS program — no AdditionalFile override
        pass
    print(f"[{label}] Starting SUMO (port {port})...")
    proc = subprocess.Popen(cmd)
    time.sleep(2.0)   # give SUMO time to open its socket

    conn = traci.connect(port=port, numRetries=10, label=label)

    # Subscribe to proximity context around the junction
    conn.junction.subscribeContext(
        JUNCTION_ID,
        tc.CMD_GET_VEHICLE_VARIABLE,
        PROXIMITY_M,
        [tc.VAR_VEHICLECLASS, tc.VAR_SPEED, tc.VAR_ROAD_ID],
    )
    print(f"[{label}] TraCI connected.")
    return proc, conn


# ---------------------------------------------------------------------------
# SimState: holds per-instance mutable state
# ---------------------------------------------------------------------------
class SimState:
    def __init__(self, label, baseline):
        self.label    = label
        self.baseline = baseline
        self.step          = 0
        self.total_co2_mg  = 0.0
        self.total_delay_s  = 0.0 # Cumulative delay for all vehicles
        self.unique_vehicles = set() # Track total unique vehicles
        self.stopped_vehicles = set() # Track vehicles currently stopped
        self.vehicle_hist  = []
        self.evp_active    = False
        self.evp_road      = None
        self.evp_start_t   = None
        self.evp_resp_s    = -1.0
        self._emerg_inject = False
        self.logic = TrafficLogic() if not baseline else None

    def avg_wait(self):
        """Calculates true Mean Delay per Vehicle."""
        total_v = len(self.unique_vehicles)
        return self.total_delay_s / total_v if total_v > 0 else 0.0

    def metrics_dict(self, vehicle_positions=None):
        return {
            "co2_mg":          round(self.total_co2_mg, 2),
            "avg_wait_s":      round(self.avg_wait(), 3),
            "vehicle_count":   self.vehicle_hist[-1] if self.vehicle_hist else 0,
            "total_vehicles":  len(self.unique_vehicles),
            "step":            self.step,
            "evp_active":      self.evp_active,
            "evp_road":        self.evp_road,
            "emergency_resp_s": self.evp_resp_s,
            "mode":            "baseline" if self.baseline else "ai",
            "positions":       vehicle_positions or []
        }


# ---------------------------------------------------------------------------
# Step one SUMO connection
# ---------------------------------------------------------------------------
def _step_conn(conn, state: SimState) -> bool:
    """Advance one step for the given traci connection. Returns False if sim ended."""
    try:
        conn.simulationStep()
    except Exception:
        return False

    state.step += 1
    vids = conn.vehicle.getIDList()

    # --- Build approach counts ---
    counts = {d: 0 for d in ("north","south","east","west",
                               "car","bus","truck","emergency","total")}
    for vid in vids:
        try:
            vcls  = conn.vehicle.getVehicleClass(vid)
            road  = conn.vehicle.getRoadID(vid)
            for appr, edges in APPROACH_EDGES.items():
                if road in edges:
                    counts[appr] += 1
            if vcls == "emergency":   counts["emergency"] += 1
            elif vcls == "bus":       counts["bus"] += 1
            elif vcls == "truck":     counts["truck"] += 1
            else:                     counts["car"] += 1
        except Exception:
            pass
    counts["total"] = len(vids)

    # --- EVP Proximity Sensor ---
    ctx = conn.junction.getContextSubscriptionResults(JUNCTION_ID) or {}
    emerg_in_range = []
    for vid, vdata in ctx.items():
        if vdata.get(tc.VAR_VEHICLECLASS, "") == "emergency":
            road = vdata.get(tc.VAR_ROAD_ID, "")
            for appr, edges in APPROACH_EDGES.items():
                if road in edges:
                    emerg_in_range.append((vid, appr))

    if emerg_in_range and not state.evp_active:
        _, appr = emerg_in_range[0]
        state.evp_active = True
        state.evp_road   = appr
        state.evp_start_t = conn.simulation.getTime()
        if state.logic:
            state.logic.priority_green_wave(appr)
        # Visual highlight for emergency vehicle
        for vid, _ in emerg_in_range:
            try:
                conn.vehicle.setColor(vid, (255, 0, 0, 255))
                conn.vehicle.highlight(vid, color=(255, 80, 0, 230), size=15, alphaMax=255)
            except Exception:
                pass
        print(f"\n[{state.label}] EVP: Emergency detected on '{appr}' at step {state.step}")

    elif not emerg_in_range and state.evp_active:
        t = conn.simulation.getTime()
        state.evp_resp_s  = round(t - state.evp_start_t, 1)
        state.evp_active  = False
        state.evp_road    = None
        if state.logic:
            state.logic.cancel_evp()
        print(f"\n[{state.label}] EVP cleared. Response time: {state.evp_resp_s}s")

    # Phase indices: 0=N_G, 1=N_Y, 2=E_G, 3=E_Y, 4=S_G, 5=S_Y, 6=W_G, 7=W_Y, 8=ALL_RED
    # Mapping for Indian 4-Phase Standard (Each approach dedicated)
    # Note: This assumes a specific TLS program layout in the .net.xml
    try:
        cur_phase = conn.trafficlight.getPhase(TLS_ID)
        phase_names = {0:"NORTH_GREEN", 1:"NORTH_YELLOW", 2:"EAST_GREEN", 3:"EAST_YELLOW", 
                       4:"SOUTH_GREEN", 5:"SOUTH_YELLOW", 6:"WEST_GREEN", 7:"WEST_YELLOW", 8:"ALL_RED"}
        pname = phase_names.get(cur_phase, f"PHASE_{cur_phase}")
    except Exception:
        return

    ns_count = counts.get("north", 0) + counts.get("south", 0)
    ew_count = counts.get("east", 0) + counts.get("west", 0)
    
    # Log phase changes
    if not hasattr(state, "last_pname"): state.last_pname = ""
    if pname != state.last_pname:
        print(f"[{state.label}] Signal: {pname}")
        state.last_pname = pname

    # --- AI Signal Override (using TrafficLogic or simplified 4-phase) ---
    if not state.baseline:
        _ai_step_signal(conn, state, counts)

    if state.step == 300 and not state._emerg_inject:
        evid = f"evp_dyn_{state.label}"
        try:
            conn.vehicle.add(
                evid, EMERGENCY_ROUTE,
                typeID=EMERGENCY_TYPE,
                depart="now",
                departLane="best",
                departSpeed="max",
            )
            conn.vehicle.setSpeedMode(evid, 7)
            conn.vehicle.setColor(evid, (255, 0, 0, 255))
            print(f"\n[{state.label}] Emergency vehicle injected at step 300")
        except Exception as e:
            print(f"\n[{state.label}] Emergency inject error: {e}")
        state._emerg_inject = True

    # --- Collect metrics ---
    step_co2 = 0.0
    new_stops = 0
    current_stopped = set()
    vehicle_positions = []
    for vid in vids:
        try:
            state.unique_vehicles.add(vid)
            # Add position tracking
            p = conn.vehicle.getPosition(vid)
            vcls = conn.vehicle.getVehicleClass(vid)
            vehicle_positions.append([p[0], p[1], vcls])
            
            step_co2 += conn.vehicle.getCO2Emission(vid)
            # Accumulate delay: vehicles slower than 0.1m/s are waiting
            speed = conn.vehicle.getSpeed(vid)
            if speed < 0.1:
                state.total_delay_s += 1.0 # +1 second per waiting vehicle
                current_stopped.add(vid)
                if vid not in state.stopped_vehicles:
                    new_stops += 1
        except Exception:
            pass
    state.stopped_vehicles = current_stopped
    state.total_co2_mg += step_co2
    state.vehicle_hist.append(len(vids))
    state.last_step_stops = new_stops
    state.last_positions = vehicle_positions

    return True


# ---------------------------------------------------------------------------
# AI Signal Control using phase index (Indian 4-Phase)
# ---------------------------------------------------------------------------
def _ai_step_signal(conn, state: SimState, counts: dict):
    # Phase indices: 0:N_G, 1:N_Y, 2:E_G, 3:E_Y, 4:S_G, 5:S_Y, 6:W_G, 7:W_Y, 8:ALL_RED
    
    # If EVP is active, immediately force the green approach
    if state.evp_active and state.evp_road:
        phase_map = {"north": 0, "east": 2, "south": 4, "west": 6}
        target_idx = phase_map.get(state.evp_road, 0)
        try:
            conn.trafficlight.setPhase(TLS_ID, target_idx)
        except Exception:
            pass
        return

    try:
        cur_phase = conn.trafficlight.getPhase(TLS_ID)
    except Exception:
        return

    # Track how many steps we've spent in the current phase
    if not hasattr(state, "phase_step"):
        state.phase_step = 0
    state.phase_step += 1

    # Yellow/All-Red transitions: Let SUMO advance them automatically
    if cur_phase in (1, 3, 5, 7, 8):
        return

    # Adaptive Logic: Only switch from Green (0, 2, 4, 6)
    MIN_GREEN = 15
    MAX_GREEN = 45

    if state.phase_step >= MIN_GREEN:
        # Determine current approach count and the maximum of others
        approach_map = {0: "north", 2: "east", 4: "south", 6: "west"}
        current_appr = approach_map.get(cur_phase)
        if not current_appr: return

        current_count = counts.get(current_appr, 0)
        others = [counts.get(a, 0) for a in ["north", "east", "south", "west"] if a != current_appr]
        max_other = max(others) if others else 0

        # Switch if other road is much busier or we hit max green
        if (max_other > current_count + 3) or (state.phase_step >= MAX_GREEN):
            # Advance to Yellow (next index)
            try:
                conn.trafficlight.setPhase(TLS_ID, cur_phase + 1)
                state.phase_step = 0
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_benchmark(steps: int = 1000, use_gui: bool = False):
    print("=" * 65)
    print("  AI-Traffic: Parallel Baseline vs AI Benchmark")
    print(f"  Steps: {steps} | Ports: 8813 (baseline) / 8814 (ai) | GUI: {use_gui}")
    print("=" * 65)

    # --- Launch SUMO instances ---
    try:
        proc_b, conn_b = _launch_sumo("baseline", 8813, baseline=True, use_gui=use_gui)
        state_b = SimState("baseline", baseline=True)
    except Exception as e:
        print(f"ERROR launching baseline: {e}")
        return

    try:
        proc_a, conn_a = _launch_sumo("ai", 8814, baseline=False, use_gui=use_gui)
        state_a = SimState("ai", baseline=False)
    except Exception as e:
        print(f"ERROR launching AI instance: {e}")
        try: conn_b.close(); proc_b.terminate()
        except Exception: pass
        return

    csv_rows = []
    csv_header = [
        "step",
        "baseline_co2_mg", "baseline_avg_wait_s", "baseline_vehicles",
        "ai_co2_mg",       "ai_avg_wait_s",       "ai_vehicles",
        "evp_active_ai", "ai_total_unique_v"
    ]

    print("\nRunning... (Ctrl+C to stop early)\n")
    try:
        for s in range(1, steps + 1):
            ok_b = _step_conn(conn_b, state_b)
            ok_a = _step_conn(conn_a, state_a)

            if not ok_b and not ok_a:
                print(f"\nBoth simulations ended at step {s}.")
                break

            # Progress
            if s % 50 == 0:
                print(
                    f"  Step {s:>5}/{steps} | "
                    f"Baseline CO2: {state_b.total_co2_mg:>10.0f}mg  Wait:{state_b.avg_wait():.2f}s | "
                    f"AI CO2: {state_a.total_co2_mg:>10.0f}mg  Wait:{state_a.avg_wait():.2f}s",
                    flush=True
                )

            # Write live metrics for dashboard polling
            try:
                live = state_a.metrics_dict(vehicle_positions=getattr(state_a, 'last_positions', []))
                with open(LIVE_JSON, "w") as f:
                    json.dump(live, f)
            except Exception:
                pass

            # CSV sample every 10 steps
            if s % 10 == 0:
                csv_rows.append([
                    s,
                    round(state_b.total_co2_mg, 2), round(state_b.avg_wait(), 3),
                    state_b.vehicle_hist[-1] if state_b.vehicle_hist else 0,
                    round(state_a.total_co2_mg, 2), round(state_a.avg_wait(), 3),
                    state_a.vehicle_hist[-1] if state_a.vehicle_hist else 0,
                    state_a.evp_active, len(state_a.unique_vehicles)
                ])

    except KeyboardInterrupt:
        print("\n[STOP] Interrupted by user.")
    finally:
        try: conn_b.close()
        except Exception: pass
        try: conn_a.close()
        except Exception: pass
        try: proc_b.terminate()
        except Exception: pass
        try: proc_a.terminate()
        except Exception: pass

    # --- Write CSV ---
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        writer.writerows(csv_rows)
    print(f"\n[OK] CSV written: {CSV_PATH}")

    # --- Compute improvements ---
    b_co2  = state_b.total_co2_mg
    a_co2  = state_a.total_co2_mg
    b_wait = state_b.avg_wait()
    a_wait = state_a.avg_wait()

    co2_pct  = round((b_co2 - a_co2) / b_co2 * 100, 2) if b_co2 > 0 else 0.0
    wait_pct = round((b_wait - a_wait) / b_wait * 100, 2) if b_wait > 0 else 0.0

    summary = {
        "steps_run":               max(state_b.step, state_a.step),
        "baseline_co2_mg":         round(b_co2, 2),
        "ai_co2_mg":               round(a_co2, 2),
        "co2_improvement_pct":     co2_pct,
        "baseline_avg_wait_s":     round(b_wait, 3),
        "ai_avg_wait_s":           round(a_wait, 3),
        "wait_improvement_pct":    wait_pct,
        "ai_evp_response_s":       state_a.evp_resp_s,
        "baseline_evp_response_s": state_b.evp_resp_s,
    }

    with open(JSON_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[OK] Summary JSON: {JSON_PATH}")

    # --- Print results ---
    print("\n" + "=" * 65)
    print("  BENCHMARK RESULTS")
    print("=" * 65)
    print(f"  Steps Completed:     {summary['steps_run']}")
    print(f"  Baseline CO2:        {b_co2:>14,.0f} mg")
    print(f"  AI-Optimized CO2:    {a_co2:>14,.0f} mg")
    print(f"  CO2 Reduction:       {co2_pct:>13.1f} %")
    print(f"  Baseline Avg Wait:   {b_wait:>14.2f} s")
    print(f"  AI Avg Wait:         {a_wait:>14.2f} s")
    print(f"  Wait Reduction:      {wait_pct:>13.1f} %")
    print(f"  AI EVP Response:     {state_a.evp_resp_s:>14.1f} s")
    print("=" * 65)
    print(f"\nFiles: {CSV_PATH}  |  {JSON_PATH}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Traffic Parallel Benchmark")
    parser.add_argument("--steps", type=int, default=1000,
                        help="Simulation steps to run (default: 1000)")
    parser.add_argument("--benchmark", action="store_true",
                        help="Alias flag for benchmark mode")
    parser.add_argument("--gui", action="store_true", default=False,
                        help="Show SUMO GUI for both instances")
    args = parser.parse_args()
    run_benchmark(steps=args.steps, use_gui=args.gui)
