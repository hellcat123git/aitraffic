import cv2
import numpy as np
from ultralytics import YOLO

class DetectionEngine:
    def __init__(self, model_path="yolov8n.pt", confidence=0.4):
        self.model = YOLO(model_path)
        self.confidence = confidence
        
        # COCO classes: 2: car, 3: motorcycle, 5: bus, 7: truck
        self.vehicle_classes = [2, 3, 5, 7]
        self.bus_class = 5
        self.truck_class = 7
        self.person_class = 0
        
        # For a hackathon, we might need a custom model for ambulances/fire trucks.
        # For now, we'll flag any "truck" or "bus" that has a high "emergency" score 
        # based on color (e.g., red for fire trucks, white/red for ambulances) 
        # OR we could use a specialized model.
        # Let's assume we can detect them via class IDs if we fine-tune.
        self.emergency_classes = [] # Placeholder for custom trained model
        
    def detect(self, frame):
        """
        Detects vehicles and returns counts and annotated frame.
        """
        results = self.model(frame, conf=self.confidence, verbose=False)
        
        counts = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "emergency": 0,
            "person": 0
        }
        
        annotated_frame = frame.copy()
        
        for box in results[0].boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            label = "Vehicle"
            color = (0, 255, 0) # Green for regular
            
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
                color = (255, 0, 0) # Blue for pedestrians
            
            # Simple heuristic for emergency vehicles (Hackathon Wow Factor)
            # In a real scenario, this would be a separate class.
            # Here we detect "Red" trucks as Fire Trucks for the demo.
            if cls_id in [5, 7]:
                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    # Red color ranges
                    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
                    mask2 = cv2.inRange(hsv, (170, 70, 50), (180, 255, 255))
                    red_ratio = (np.sum(mask1) + np.sum(mask2)) / (roi.size * 255)
                    
                    if red_ratio > 0.1: # If more than 10% of the vehicle is red
                        counts["emergency"] += 1
                        label = "EMERGENCY"
                        color = (0, 0, 255) # Red for emergency
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                        
        return counts, annotated_frame
