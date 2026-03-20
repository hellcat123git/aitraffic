class EcoTracker:
    def __init__(self):
        # Emissions in kg/second for an idling vehicle (Average)
        self.CO2_PER_SEC = 0.00066 # Approx 2.4kg/hr
        self.total_co2_saved = 0.0
        
        # Assume a standard static signal waits for 60s
        self.STATIC_WAIT_TIME = 60.0
        
    def calculate_savings(self, vehicle_count, adaptive_wait_time):
        """
        Calculates CO2 saved by comparing adaptive wait time vs static wait time.
        """
        if adaptive_wait_time < self.STATIC_WAIT_TIME:
            saved_time = self.STATIC_WAIT_TIME - adaptive_wait_time
            saved_co2 = saved_time * self.CO2_PER_SEC * vehicle_count
            self.total_co2_saved += saved_co2
            return saved_co2
        return 0.0
        
    def get_total_saved(self):
        return round(self.total_co2_saved, 4)
