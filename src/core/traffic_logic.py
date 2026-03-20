import time

class TrafficLogic:
    def __init__(self, min_green=10, max_green=30, yellow_time=3):
        self.min_green = min_green
        self.max_green = max_green
        self.yellow_time = yellow_time
        
        self.current_road = 1 # Start with Road 1
        self.state = "GREEN" # Possible: GREEN, YELLOW, RED
        self.start_time = time.time()
        self.last_switch_time = time.time()
        
        # Roads data
        self.roads = {
            1: {"count": 0, "emergency": 0},
            2: {"count": 0, "emergency": 0}
        }
        
    def update_road_stats(self, road_id, count, emergency=0):
        if road_id in self.roads:
            self.roads[road_id]["count"] = count
            self.roads[road_id]["emergency"] = emergency
            
    def get_signal_states(self):
        """
        Returns the current signal for each road.
        """
        if self.current_road == 1:
            if self.state == "GREEN":
                return "GREEN", "RED"
            elif self.state == "YELLOW":
                return "YELLOW", "RED"
        else: # Current road 2
            if self.state == "GREEN":
                return "RED", "GREEN"
            elif self.state == "YELLOW":
                return "RED", "YELLOW"
        return "RED", "RED"

    def decide(self):
        """
        The core decision logic.
        """
        now = time.time()
        elapsed = now - self.start_time
        
        # 1. Emergency Preemption (Highest Priority)
        # If road 1 has emergency but road 2 is green, switch immediately.
        if self.roads[1]["emergency"] > 0 and self.current_road == 2:
            if self.state == "GREEN":
                self.state = "YELLOW"
                self.start_time = now
                return "SWITCH_TO_1_EMERGENCY"
        
        if self.roads[2]["emergency"] > 0 and self.current_road == 1:
            if self.state == "GREEN":
                self.state = "YELLOW"
                self.start_time = now
                return "SWITCH_TO_2_EMERGENCY"

        # 2. Normal Adaptive Logic
        if self.state == "GREEN":
            # Minimum green time must pass
            if elapsed >= self.min_green:
                other_road = 2 if self.current_road == 1 else 1
                
                # Switch if other road is congested or we exceeded max green
                if (self.roads[other_road]["count"] > self.roads[self.current_road]["count"] + 2) or \
                   (elapsed >= self.max_green):
                    self.state = "YELLOW"
                    self.start_time = now
                    return "TRANSITION"
                    
        elif self.state == "YELLOW":
            if elapsed >= self.yellow_time:
                # Toggle current road
                self.current_road = 2 if self.current_road == 1 else 1
                self.state = "GREEN"
                self.start_time = now
                return "SWITCH_COMPLETE"
                
        return "STAY"
