import time


class EcoTracker:
    """
    Tracks CO2 emissions and wait-time savings.

    Supports two data sources:
    1. Heuristic mode (--mode video): estimates savings vs a fixed-cycle baseline.
    2. TraCI mode (--mode sumo): ingests real per-vehicle data from SUMO.
    """

    # Heuristic constant — CO2 for an idling vehicle (kg/s)
    CO2_PER_SEC_KG = 0.00066   # ≈ 2.4 kg/hr

    # Scientific constant — CO2 penalty for one re-acceleration event (0 to 50 km/h)
    # Based on average passenger car VSP models.
    REACCEL_PENALTY_KG = 0.045  # ~45g per stop-start event
    
    # TraCI (SUMO) specific penalty in milligrams
    STOP_COUNT_PENALTY_MG = 45000.0

    # Assumed fixed-cycle green duration for heuristic comparison
    STATIC_WAIT_TIME = 60.0    # seconds

    def __init__(self):
        # Heuristic tracking (video mode)
        self._heuristic_co2_saved_kg = 0.0

        # TraCI tracking (SUMO mode)
        self._traci_co2_baseline_mg = 0.0   # accumulated during baseline run
        self._traci_co2_ai_mg = 0.0         # accumulated during AI-driven run
        self._traci_wait_baseline_s = []    # list of per-step avg wait (baseline)
        self._traci_wait_ai_s = []          # list of per-step avg wait (AI)
        self._current_mode = "video"         # 'video' | 'sumo_baseline' | 'sumo_ai'
        
        # New: Tracking unique stops to apply re-acceleration penalty in SUMO mode
        self._baseline_stops = 0
        self._ai_stops = 0

        # Emergency vehicle response time
        self._evp_start_time = None
        self._evp_response_time_s = -1.0

    # ------------------------------------------------------------------
    # Heuristic mode (video)
    # ------------------------------------------------------------------

    def calculate_savings(self, vehicle_count, adaptive_wait_time):
        """
        Estimates CO2 saved by comparing adaptive wait vs static 60-second cycle.
        Accounts for idling time AND the stop-start penalty.
        """
        if adaptive_wait_time < self.STATIC_WAIT_TIME:
            saved_time = self.STATIC_WAIT_TIME - adaptive_wait_time
            
            # 1. Savings from reduced idling
            idle_savings = saved_time * self.CO2_PER_SEC_KG * vehicle_count
            
            # 2. Offset by re-acceleration penalty
            # We assume all vehicles that 'waited' at the signal
            # incur one re-acceleration penalty when it turns green.
            stop_start_cost = vehicle_count * self.REACCEL_PENALTY_KG
            
            total_saved = idle_savings - stop_start_cost
            self._heuristic_co2_saved_kg += total_saved
            return round(total_saved, 6)
        return 0.0

    def get_total_saved(self):
        """Returns cumulative CO2 saved in heuristic video mode (kg)."""
        return round(self._heuristic_co2_saved_kg, 4)

    # ------------------------------------------------------------------
    # TraCI mode (SUMO)
    # ------------------------------------------------------------------

    def set_sumo_mode(self, mode):
        """
        Set the active SUMO collection mode.

        Args:
            mode (str): 'sumo_baseline' or 'sumo_ai'
        """
        assert mode in ("sumo_baseline", "sumo_ai"), f"Unknown mode: {mode}"
        self._current_mode = mode

    def ingest_traci_metrics(self, co2_mg, avg_wait_s, new_stops=0):
        """
        Accumulate one simulation step's worth of TraCI emissions and wait data.

        Args:
            co2_mg (float): Total CO2 emitted by all vehicles this step (mg).
            avg_wait_s (float): Mean waiting time across all vehicles (seconds).
            new_stops (int): Number of vehicles that just came to a halt.
        """
        penalty = new_stops * self.STOP_COUNT_PENALTY_MG
        
        if self._current_mode == "sumo_baseline":
            self._traci_co2_baseline_mg += (co2_mg + penalty)
            self._traci_wait_baseline_s.append(avg_wait_s)
            self._baseline_stops += new_stops
        elif self._current_mode == "sumo_ai":
            self._traci_co2_ai_mg += (co2_mg + penalty)
            self._traci_wait_ai_s.append(avg_wait_s)
            self._ai_stops += new_stops

    def record_evp_start(self):
        """Mark the moment an emergency vehicle is detected."""
        self._evp_start_time = time.time()

    def record_evp_cleared(self):
        """Mark the moment the emergency vehicle clears the intersection."""
        if self._evp_start_time is not None:
            self._evp_response_time_s = round(time.time() - self._evp_start_time, 2)
            self._evp_start_time = None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_live_metrics(self):
        """
        Returns current metrics in a format suitable for the Streamlit dashboard.
        Works in all modes.
        """
        if self._current_mode == "video":
            return {
                "mode": "video",
                "co2_saved_kg": self.get_total_saved(),
                "co2_ai_mg": 0.0,
                "avg_wait_ai_s": 0.0,
                "emergency_resp_s": -1.0,
            }

        ai_wait = (
            sum(self._traci_wait_ai_s) / len(self._traci_wait_ai_s)
            if self._traci_wait_ai_s
            else 0.0
        )
        return {
            "mode": self._current_mode,
            "co2_ai_mg": round(self._traci_co2_ai_mg, 2),
            "avg_wait_ai_s": round(ai_wait, 3),
            "co2_saved_kg": 0.0,  # Not meaningful mid-run
            "emergency_resp_s": self._evp_response_time_s,
        }

    def get_benchmark_report(self):
        """
        Generate the side-by-side comparison dict for the Judges' Report.
        Should be called after both baseline and AI-driven runs are complete.

        Returns:
            dict with keys: baseline_co2, ai_co2, co2_improvement_pct,
                            baseline_avg_wait, ai_avg_wait, wait_improvement_pct,
                            evp_response_s
        """
        b_co2 = self._traci_co2_baseline_mg
        a_co2 = self._traci_co2_ai_mg

        b_wait = (
            sum(self._traci_wait_baseline_s) / len(self._traci_wait_baseline_s)
            if self._traci_wait_baseline_s else 0.0
        )
        a_wait = (
            sum(self._traci_wait_ai_s) / len(self._traci_wait_ai_s)
            if self._traci_wait_ai_s else 0.0
        )

        co2_pct = round((b_co2 - a_co2) / b_co2 * 100, 2) if b_co2 > 0 else 0.0
        wait_pct = round((b_wait - a_wait) / b_wait * 100, 2) if b_wait > 0 else 0.0

        return {
            "baseline_co2_mg": round(b_co2, 2),
            "ai_co2_mg": round(a_co2, 2),
            "co2_improvement_pct": co2_pct,
            "baseline_avg_wait_s": round(b_wait, 3),
            "ai_avg_wait_s": round(a_wait, 3),
            "wait_improvement_pct": wait_pct,
            "evp_response_s": self._evp_response_time_s,
        }
