"""
SumoEngine — TraCI-based simulation engine for AI-Traffic.

Implements BaseEngine using SUMO (Simulation of Urban MObility) via the
traci Python library. Acts as a drop-in replacement for DetectionEngine
in --mode sumo.

Prerequisites:
    - SUMO installed (eclipse-sumo or system package)
    - SUMO_HOME environment variable set
    - traci package installed (already in requirements.txt)
"""

import os
import sys
import time
import json
import traceback

from src.core.base_engine import BaseEngine

# ---------------------------------------------------------------------------
# TraCI import with helpful error message
# ---------------------------------------------------------------------------
try:
    import traci
    import traci.constants as tc
except ImportError:
    raise ImportError(
        "[SumoEngine] 'traci' package not found.\n"
        "  Install it with:  pip install traci\n"
        "  Also ensure SUMO binaries are installed and SUMO_HOME is set."
    )


# ---------------------------------------------------------------------------
# SUMO binary resolution
# ---------------------------------------------------------------------------
def _resolve_sumo_binary(gui: bool) -> str:
    """Return the full path to the sumo / sumo-gui binary."""
    binary_name = "sumo-gui" if gui else "sumo"

    sumo_home = os.environ.get("SUMO_HOME", "")
    if sumo_home:
        candidate = os.path.join(sumo_home, "bin", binary_name)
        if os.path.isfile(candidate):
            return candidate
        # Windows adds .exe
        candidate_exe = candidate + ".exe"
        if os.path.isfile(candidate_exe):
            return candidate_exe

    # Fall back to PATH
    return binary_name


# ---------------------------------------------------------------------------
# Approach-lane mapping
# ---------------------------------------------------------------------------
# Maps human-readable approach name → list of SUMO edge IDs entering center
APPROACH_EDGES = {
    "north": ["north_in"],
    "south": ["south_in"],
    "east":  ["east_in"],
    "west":  ["west_in"],
}

# SUMO TLS junction ID in our scenario
JUNCTION_ID = "center"
TLS_ID = "center"

# Emergency vehicle proximity sensor radius (metres)
PROXIMITY_RADIUS_M = 200.0

# Emergency vehicle route ID (defined in rou.xml)
EMERGENCY_ROUTE_ID = "west_to_east"
EMERGENCY_VEHICLE_TYPE = "emergency_car"


class SumoEngine(BaseEngine):
    """
    SUMO TraCI engine.  Manages the full simulation lifecycle:
        start → step loop → EVP detection → metrics collection → close.
    """

    def __init__(
        self,
        config: str = "sumo/intersection.sumocfg",
        gui: bool = True,
        baseline: bool = False,
        port: int = 8813,
        metrics_output: str = None,
    ):
        """
        Args:
            config      : Path to the .sumocfg file.
            gui         : If True, launch sumo-gui; otherwise headless sumo.
            baseline    : If True, do NOT override the TLS via TraCI (fixed-time runs).
            port        : TraCI port to use (default 8813).
            metrics_output: Path to write live JSON metrics at each step (for dashboard).
        """
        self.config = config
        self.gui = gui
        self.baseline = baseline
        self.port = port
        self.metrics_output = metrics_output

        # Runtime state
        self._step = 0
        self._emergency_injected = False
        self._evp_active = False
        self._evp_approaching_road = None
        self._evp_start_sim_time = None
        self._evp_response_sim_s = -1.0

        # Accumulated metrics
        self._total_co2_mg = 0.0
        self._wait_samples = []
        self._vehicle_count_history = []

        # Traffic logic reference (set externally via set_logic())
        self._logic = None

        self._start_sumo()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start_sumo(self):
        """Launch SUMO subprocess and connect TraCI."""
        binary = _resolve_sumo_binary(self.gui)
        sumo_cmd = [
            binary,
            "-c", self.config,
            "--no-step-log",
            "--no-warnings",
            "--collision.action", "warn",
            "--time-to-teleport", "300",
        ]

        if not self.gui:
            sumo_cmd += ["--no-step-log", "true"]

        print(f"[SumoEngine] Starting SUMO: {' '.join(sumo_cmd)}")
        traci.start(sumo_cmd, port=self.port)

        # Subscribe to context around junction center for proximity sensor
        traci.junction.subscribeContext(
            JUNCTION_ID,
            tc.CMD_GET_VEHICLE_VARIABLE,
            PROXIMITY_RADIUS_M,
            [tc.VAR_VEHICLECLASS, tc.VAR_SPEED, tc.VAR_ROAD_ID],
        )

        print("[SumoEngine] TraCI connected. Simulation ready.")

    def release(self):
        """Close TraCI and terminate SUMO."""
        try:
            traci.close()
            print("[SumoEngine] TraCI closed.")
        except Exception:
            pass  # Already closed

    def set_logic(self, logic):
        """
        Attach a TrafficLogic instance so SumoEngine can trigger EVP.

        Args:
            logic: TrafficLogic instance.
        """
        self._logic = logic

    # ------------------------------------------------------------------
    # BaseEngine.detect
    # ------------------------------------------------------------------

    def detect(self, source=None):
        """
        Advance the simulation by one step and return vehicle state.

        Returns:
            tuple: (counts dict, None)
                counts keys: 'north', 'south', 'east', 'west',
                             'car', 'bus', 'truck', 'emergency', 'total'
        """
        try:
            traci.simulationStep()
        except traci.exceptions.FatalTraCIError as e:
            print(f"[SumoEngine] Simulation ended: {e}")
            return self._empty_counts(), None

        self._step += 1

        # -- Build per-approach vehicle counts --
        counts = {
            "north": 0, "south": 0, "east": 0, "west": 0,
            "car": 0, "bus": 0, "truck": 0, "motorcycle": 0,
            "person": 0, "emergency": 0, "total": 0,
        }

        vehicle_ids = traci.vehicle.getIDList()

        for vid in vehicle_ids:
            try:
                vclass = traci.vehicle.getVehicleClass(vid)
                road_id = traci.vehicle.getRoadID(vid)

                # Approach counting
                for approach, edges in APPROACH_EDGES.items():
                    if road_id in edges:
                        counts[approach] += 1

                # Type counting
                if vclass == "emergency":
                    counts["emergency"] += 1
                elif vclass == "bus":
                    counts["bus"] += 1
                elif vclass == "truck":
                    counts["truck"] += 1
                else:
                    counts["car"] += 1

            except traci.exceptions.TraCIException:
                continue  # Vehicle may have arrived/teleported between calls

        counts["total"] = len(vehicle_ids)

        # -- Proximity sensor: EVP detection --
        self._check_evp_sensor(counts)

        # -- Collect emissions & wait time --
        self._collect_metrics(vehicle_ids)

        # -- Write live metrics JSON for dashboard --
        if self.metrics_output:
            self._write_metrics_json()

        return counts, None  # SUMO-GUI handles visuals

    # ------------------------------------------------------------------
    # EVP Proximity Sensor
    # ------------------------------------------------------------------

    def _check_evp_sensor(self, counts):
        """
        Inspect context subscription results for emergency vehicles within
        PROXIMITY_RADIUS_M of the intersection center.

        When detected: triggers priority_green_wave on the correct approach.
        When cleared:  cancels EVP and records response time.
        """
        context_results = traci.junction.getContextSubscriptionResults(JUNCTION_ID)
        emergency_in_range = []

        if context_results:
            for vid, var_data in context_results.items():
                vclass = var_data.get(tc.VAR_VEHICLECLASS, "")
                if vclass == "emergency":
                    road_id = var_data.get(tc.VAR_ROAD_ID, "")
                    # Determine which approach the EV is on
                    for approach, edges in APPROACH_EDGES.items():
                        if road_id in edges:
                            emergency_in_range.append((vid, approach))

        if emergency_in_range and not self._evp_active:
            # Emergency vehicle entered the detection zone
            _, approach = emergency_in_range[0]
            self._evp_active = True
            self._evp_approaching_road = approach
            self._evp_start_sim_time = traci.simulation.getTime()

            if self._logic:
                self._logic.priority_green_wave(approach)

            # Visual: set vehicle color to bright red in SUMO-GUI
            for vid, _ in emergency_in_range:
                try:
                    traci.vehicle.setColor(vid, (255, 0, 0, 255))
                    traci.vehicle.highlight(vid, color=(255, 80, 0, 230), size=15, alphaMax=255)
                except Exception:
                    pass

        elif not emergency_in_range and self._evp_active:
            # Emergency vehicle left the detection zone — clear EVP
            cleared_sim_time = traci.simulation.getTime()
            self._evp_response_sim_s = round(
                cleared_sim_time - self._evp_start_sim_time, 1
            )
            self._evp_active = False
            self._evp_approaching_road = None

            if self._logic:
                self._logic.cancel_evp()

    # ------------------------------------------------------------------
    # TraCI Signal Override (AI mode only)
    # ------------------------------------------------------------------

    def apply_signal(self, phase_string: str):
        """
        Write the TrafficLogic phase string to the SUMO TLS.
        Called in AI-driven mode; skipped in baseline mode.

        Args:
            phase_string (str): 12-character SUMO TLS state string.
        """
        if self.baseline:
            return  # Let SUMO's built-in fixed-time program run

        try:
            # Pad/trim to match actual link count if needed
            traci.trafficlight.setRedYellowGreenState(TLS_ID, phase_string)
        except traci.exceptions.TraCIException as e:
            pass  # TLS may not exist in all scenarios

    # ------------------------------------------------------------------
    # Emergency Injection
    # ------------------------------------------------------------------

    def inject_emergency(self, route_id: str = EMERGENCY_ROUTE_ID):
        """
        Programmatically add an emergency vehicle at the west edge of the network.

        Args:
            route_id (str): SUMO route ID defined in rou.xml.
        """
        if self._emergency_injected:
            print("[SumoEngine] Emergency vehicle already injected.")
            return

        veh_id = "evp_dynamic_001"
        try:
            traci.vehicle.add(
                vehID=veh_id,
                routeID=route_id,
                typeID=EMERGENCY_VEHICLE_TYPE,
                depart="now",
                departLane="best",
                departSpeed="max",
            )
            traci.vehicle.setColor(veh_id, (255, 0, 0, 255))
            traci.vehicle.setSpeedMode(veh_id, 7)   # Ignore traffic lights
            self._emergency_injected = True
            print(f"[SumoEngine] Emergency vehicle '{veh_id}' injected on route '{route_id}'.")
        except traci.exceptions.TraCIException as e:
            print(f"[SumoEngine] Failed to inject emergency vehicle: {e}")

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _collect_metrics(self, vehicle_ids):
        """Accumulate per-step CO2 and wait-time data."""
        step_co2 = 0.0
        step_waits = []

        for vid in vehicle_ids:
            try:
                step_co2 += traci.vehicle.getCO2Emission(vid)      # mg/s
                step_waits.append(traci.vehicle.getWaitingTime(vid))  # seconds
            except traci.exceptions.TraCIException:
                continue

        self._total_co2_mg += step_co2
        self._vehicle_count_history.append(len(vehicle_ids))
        if step_waits:
            self._wait_samples.append(sum(step_waits) / len(step_waits))

    def get_metrics(self):
        """Return cumulative metrics dict (BaseEngine contract)."""
        avg_wait = (
            sum(self._wait_samples) / len(self._wait_samples)
            if self._wait_samples else 0.0
        )
        return {
            "co2_mg": round(self._total_co2_mg, 2),
            "avg_wait_s": round(avg_wait, 3),
            "emergency_resp_s": self._evp_response_sim_s,
            "vehicle_count": (
                self._vehicle_count_history[-1]
                if self._vehicle_count_history else 0
            ),
            "step": self._step,
            "evp_active": self._evp_active,
            "evp_road": self._evp_approaching_road,
        }

    def _write_metrics_json(self):
        """Write live metrics to JSON file for Streamlit dashboard polling."""
        try:
            with open(self.metrics_output, "w") as f:
                json.dump(self.get_metrics(), f)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _empty_counts():
        return {
            "north": 0, "south": 0, "east": 0, "west": 0,
            "car": 0, "bus": 0, "truck": 0, "motorcycle": 0,
            "person": 0, "emergency": 0, "total": 0,
        }

    def current_sim_time(self):
        """Return current simulation time in seconds."""
        try:
            return traci.simulation.getTime()
        except Exception:
            return self._step
