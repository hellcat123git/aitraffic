from abc import ABC, abstractmethod


class BaseEngine(ABC):
    """
    Abstract base class for all detection/simulation engines.
    Both DetectionEngine (YOLOv8) and SumoEngine (TraCI) implement this interface,
    making them drop-in replacements for each other.
    """

    @abstractmethod
    def detect(self, source=None):
        """
        Run one detection/simulation step and return vehicle state.

        Args:
            source: For DetectionEngine — a raw video frame (numpy array).
                    For SumoEngine — ignored (advances simulation by one step).

        Returns:
            tuple: (counts, frame)
                - counts (dict): Vehicle counts keyed by approach road.
                  Guaranteed keys: 'car', 'motorcycle', 'bus', 'truck',
                  'emergency', 'person', 'total'.
                  SumoEngine also adds per-approach keys:
                  'north', 'south', 'east', 'west'.
                - frame: Annotated BGR frame (numpy array) for DetectionEngine,
                  or None for SumoEngine (SUMO-GUI handles visuals).
        """
        pass

    @abstractmethod
    def get_metrics(self):
        """
        Return the latest performance and eco metrics.

        Returns:
            dict with guaranteed keys:
                'co2_mg'           (float) — cumulative CO2 emitted this session (mg)
                'avg_wait_s'       (float) — average vehicle waiting time (seconds)
                'emergency_resp_s' (float) — seconds from detection to green wave
                                             (-1.0 if no emergency event yet)
                'vehicle_count'    (int)   — current number of active vehicles
        """
        pass

    @abstractmethod
    def inject_emergency(self, route_id="west_to_east"):
        """
        Programmatically insert an emergency vehicle.

        Args:
            route_id (str): The SUMO route ID the emergency vehicle should follow.
                            Ignored (no-op) in DetectionEngine mode.
        """
        pass

    @abstractmethod
    def release(self):
        """
        Clean up all resources (close TraCI connection, release OpenCV captures, etc.).
        """
        pass
