import time


class TrafficLogic:
    """
    Adaptive traffic signal controller supporting 2-road (video mode)
    and 4-road (N/S/E/W SUMO mode) operation.

    Road IDs can be integers (1, 2) or strings ('north', 'south', 'east', 'west').
    The controller auto-detects mode based on which road IDs are registered via
    update_road_stats().
    """

    # --- SUMO TLS phase string constants (20-link 4-arm intersection) ---
    # Indian 4-Phase Standard: Each approach gets its own dedicated green.
    # N(0-4), S(5-9), E(10-14), W(15-19)
    _PHASE_NORTH_GREEN  = "GGGGgrrrrrrrrrrrrrrr"
    _PHASE_SOUTH_GREEN  = "rrrrrGGGGgrrrrrrrrrr"
    _PHASE_EAST_GREEN   = "rrrrrrrrrrGGGGgrrrrr"
    _PHASE_WEST_GREEN   = "rrrrrrrrrrrrrrrGGGGg"
    
    _PHASE_NORTH_YELLOW = "yyyyyrrrrrrrrrrrrrrr"
    _PHASE_SOUTH_YELLOW = "rrrrryyyyyrrrrrrrrrr"
    _PHASE_EAST_YELLOW  = "rrrrrrrrrryyyyyrrrrr"
    _PHASE_WEST_YELLOW  = "rrrrrrrrrrrrrrryyyyy"
    
    _PHASE_ALL_RED      = "rrrrrrrrrrrrrrrrrrrr"

    # Per-approach greenlight strings for priority green wave (20-char)
    _APPROACH_GREEN = {
        "north": _PHASE_NORTH_GREEN,
        "south": _PHASE_SOUTH_GREEN,
        "east":  _PHASE_EAST_GREEN,
        "west":  _PHASE_WEST_GREEN,
        1:       _PHASE_NORTH_GREEN, # Mapping for 2-way mode compatibility
        2:       _PHASE_SOUTH_GREEN,
    }

    def __init__(self, min_green=15, max_green=45, yellow_time=3, all_red_time=1):
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_time = yellow_time
        self.all_red_time = all_red_time # Indian standard clearance

        # Road state storage — populated lazily via update_road_stats()
        self.roads = {}

        # Phase tracking
        self.current_road = None     # Active green road ID
        self.state = "GREEN"         # GREEN, YELLOW, or ALL_RED
        self.start_time = time.time()

        # EVP tracking
        self.evp_active = False
        self.evp_road = None
        
        # 4-Phase Rotation Order (Indian Style)
        self.rotation_order = ["north", "east", "south", "west"]

    # ------------------------------------------------------------------
    # Signal state queries
    # ------------------------------------------------------------------

    def get_signal_states(self):
        """
        Returns a dict mapping road_id → signal colour ('GREEN'/'YELLOW'/'RED').
        """
        signals = {}
        for road_id in self.roads:
            if road_id == self.current_road:
                signals[road_id] = self.state if self.state != "ALL_RED" else "RED"
            else:
                signals[road_id] = "RED"
        return signals

    def get_traci_phase_string(self):
        """
        Returns a 20-char SUMO TLS state string for the current phase.
        """
        if self.state == "ALL_RED":
            return self._PHASE_ALL_RED

        if self.evp_active and self.evp_road is not None:
            return self._APPROACH_GREEN.get(self.evp_road, self._PHASE_ALL_RED)

        if self.current_road == "north" or self.current_road == 1:
            return self._PHASE_NORTH_GREEN if self.state == "GREEN" else self._PHASE_NORTH_YELLOW
        elif self.current_road == "east":
            return self._PHASE_EAST_GREEN if self.state == "GREEN" else self._PHASE_EAST_YELLOW
        elif self.current_road == "south" or self.current_road == 2:
            return self._PHASE_SOUTH_GREEN if self.state == "GREEN" else self._PHASE_SOUTH_YELLOW
        elif self.current_road == "west":
            return self._PHASE_WEST_GREEN if self.state == "GREEN" else self._PHASE_WEST_YELLOW
        
        return self._PHASE_ALL_RED

    # ------------------------------------------------------------------
    # Core decision logic
    # ------------------------------------------------------------------

    def decide(self):
        """
        Run one decision cycle with safety-first transitions (GREEN -> YELLOW -> ALL_RED).
        """
        now = time.time()
        elapsed = now - self.start_time

        if not self.roads or self.current_road is None:
            return "STAY"

        # 1. Handle EVP Transition (Safety Yellow + All Red)
        if self.evp_active:
            if self.state == "YELLOW" and hasattr(self, 'next_evp_road') and self.next_evp_road:
                if elapsed >= self.yellow_time:
                    self.state = "ALL_RED"
                    self.start_time = now
                    return "TRANSITION_TO_ALL_RED"
                return "EVP_YELLOW"
            
            if self.state == "ALL_RED" and hasattr(self, 'next_evp_road') and self.next_evp_road:
                if elapsed >= self.all_red_time:
                    self.current_road = self.next_evp_road
                    self.state = "GREEN"
                    self.start_time = now
                    self.next_evp_road = None
                    return "EVP_SWITCH_COMPLETE"
                return "EVP_ALL_RED"
            
            return "EVP_HOLD"

        # 2. Normal adaptive logic
        if self.state == "GREEN":
            # Check for emergency vehicles first
            for road_id, data in self.roads.items():
                if data["emergency"] > 0 and road_id != self.current_road:
                    self.priority_green_wave(road_id)
                    return f"SWITCH_TO_{str(road_id).upper()}_EMERGENCY"

            if elapsed >= self.min_green:
                current_count = self.roads[self.current_road]["count"]
                
                # Look for high demand on other roads
                others = [r for r in self.roads if r != self.current_road]
                max_other = max([self.roads[r]["count"] for r in others]) if others else 0

                if (max_other > current_count + 3) or (elapsed >= self.max_green):
                    self.state = "YELLOW"
                    self.start_time = now
                    return "TRANSITION"

        elif self.state == "YELLOW":
            if elapsed >= self.yellow_time:
                self.state = "ALL_RED"
                self.start_time = now
                return "TRANSITION_TO_ALL_RED"

        elif self.state == "ALL_RED":
            if elapsed >= self.all_red_time:
                # Rotate to road with highest vehicle count
                road_ids = list(self.roads.keys())
                # Use Indian rotation preference (North -> East -> South -> West)
                # but weighted by vehicle count.
                others = [r for r in road_ids if r != self.current_road]
                if others:
                    # Priority given to road with highest count
                    self.current_road = max(others, key=lambda r: self.roads[r]["count"])
                
                self.state = "GREEN"
                self.start_time = now
                return "SWITCH_COMPLETE"

        return "STAY"
