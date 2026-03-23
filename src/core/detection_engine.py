import cv2
import numpy as np
from ultralytics import YOLO
from src.core.base_engine import BaseEngine


class DetectionEngine(BaseEngine):
    """
    YOLOv8-based vehicle detection engine.
    Implements BaseEngine for use in --mode video.
    """

    def __init__(self, model_path="yolov8n.pt", confidence=0.4):
        self.model = YOLO(model_path)
        self.confidence = confidence

        # COCO class IDs
        self.vehicle_classes = [2, 3, 5, 7]
        self.bus_class = 5
        self.truck_class = 7
        self.person_class = 0
        self.emergency_classes = []  # Placeholder for custom-trained model

    # ------------------------------------------------------------------
    # BaseEngine interface
    # ------------------------------------------------------------------

    def detect(self, source=None):
        """
        Run YOLOv8 inference on a single frame.

        Args:
            source: BGR numpy array (video frame). Required in video mode.

        Returns:
            tuple: (counts dict, annotated frame)
        """
        frame = source
        results = self.model(frame, conf=self.confidence, verbose=False)

        counts = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "emergency": 0,
            "person": 0,
            "total": 0,
            # Per-approach keys not populated in video mode (single camera)
        }

        annotated_frame = frame.copy()

        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            label = "Vehicle"
            color = (0, 255, 0)  # Green for regular vehicles

            if cls_id == 2:
                counts["car"] += 1
                label = "Car"
            elif cls_id == 3:
                counts["motorcycle"] += 1
                label = "Motorcycle"
            elif cls_id == 5:
                counts["bus"] += 1
                label = "Bus"
            elif cls_id == 7:
                counts["truck"] += 1
                label = "Truck"
            elif cls_id == 0:
                counts["person"] += 1
                label = "Pedestrian"
                color = (255, 0, 0)  # Blue for pedestrians

            # Emergency vehicle heuristic: detect red-dominant buses/trucks
            if cls_id in [5, 7]:
                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
                    mask2 = cv2.inRange(hsv, (170, 70, 50), (180, 255, 255))
                    red_ratio = (np.sum(mask1) + np.sum(mask2)) / (roi.size * 255)

                    if red_ratio > 0.1:
                        counts["emergency"] += 1
                        label = "EMERGENCY"
                        color = (0, 0, 255)

            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated_frame,
                f"{label} {conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )

        counts["total"] = (
            counts["car"] + counts["motorcycle"] + counts["bus"] + counts["truck"]
        )

        return counts, annotated_frame

    def get_metrics(self):
        """
        YOLOv8 mode has no real-time emissions data — returns zeroed metrics.
        CO2 savings are computed heuristically by EcoTracker instead.
        """
        return {
            "co2_mg": 0.0,
            "avg_wait_s": 0.0,
            "emergency_resp_s": -1.0,
            "vehicle_count": 0,
        }

    def inject_emergency(self, route_id="west_to_east"):
        """No-op in YOLO mode — emergencies are detected visually."""
        print(
            "[DetectionEngine] inject_emergency() is a no-op in video mode. "
            "Emergency vehicles must appear in the camera feed."
        )

    def release(self):
        """DetectionEngine holds no persistent resources beyond the YOLO model."""
        pass
