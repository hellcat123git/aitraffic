"""
adaptive_traffic_yolo.py
Adaptive traffic light for 2 roads using 2 webcams + YOLOv8 detection + centroid tracking.
Requires: pip install ultralytics
"""

import time
import math
from collections import deque

import cv2
import numpy as np
from ultralytics import YOLO

# ---------- User settings ----------
CAM0 = 0                 # camera index for road 0
CAM1 = 1                 # camera index for road 1
FRAME_WIDTH = 640
FRAME_HEIGHT = 360

# Detector settings
YOLO_WEIGHTS = "yolov8n.pt"   # small model (downloads automatically)
IMG_SIZE = 640                # try 640 (higher -> more accurate and slower)
CONF_THRESH = 0.35            # increase to 0.45-0.5 to reduce false positives
IOU_THRESH = 0.45

# Counting / tracker tuning
LINE_POS_RATIO = 0.6    # line at 60% height (adjust so vehicles cross it)
MAX_TRACKER_DISTANCE = 80
TRACKER_MAX_DISAPPEARED = 8

# Adaptive traffic timing
MIN_GREEN = 5
MAX_GREEN = 20
HYSTERESIS = 2

AVG_WINDOW_SECONDS = 2.0
FPS_ESTIMATE = 12

SHOW_WINDOWS = True

# Which COCO class IDs represent vehicles: car=2, motorcycle=3, bus=5, truck=7
VEHICLE_CLASS_IDS = {2, 3, 5, 7}

# Optional serial (set USE_SERIAL True and configure COM/baud)
USE_SERIAL = False
SERIAL_PORT = "COM3"
SERIAL_BAUD = 9600

# ---------- Helpers ----------
if USE_SERIAL:
    import serial
    try:
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        print(f"Opened serial {SERIAL_PORT}@{SERIAL_BAUD}")
    except Exception as e:
        print("Failed to open serial:", e)
        ser = None
else:
    ser = None

def send_serial(state):
    if ser is None:
        return
    cmd = "G0\n" if state == 0 else "G1\n"
    try:
        ser.write(cmd.encode())
    except Exception as e:
        print("Serial send failed:", e)

class VehicleCounter:
    def __init__(self, avg_window_seconds=AVG_WINDOW_SECONDS, fps=FPS_ESTIMATE):
        buf_len = max(1, int(round(avg_window_seconds * fps)))
        self.buf = deque(maxlen=buf_len)

    def push(self, value):
        self.buf.append(value)

    def avg(self):
        if not self.buf:
            return 0.0
        return sum(self.buf) / len(self.buf)

# Small centroid tracker (greedy matching)
class CentroidTracker:
    def __init__(self, max_disappeared=TRACKER_MAX_DISAPPEARED, max_distance=MAX_TRACKER_DISTANCE):
        self.next_id = 0
        self.objects = {}            # id -> (cx,cy)
        self.disappeared = {}        # id -> frames disappeared
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.counted_ids = set()     # ids that were counted (crossed the line)

    def register(self, centroid):
        self.objects[self.next_id] = centroid
        self.disappeared[self.next_id] = 0
        self.next_id += 1

    def deregister(self, oid):
        if oid in self.objects:
            del self.objects[oid]
        if oid in self.disappeared:
            del self.disappeared[oid]
        if oid in self.counted_ids:
            self.counted_ids.discard(oid)

    def update(self, rects):
        # rects: list of (x1,y1,x2,y2)
        if len(rects) == 0:
            # mark disappeared
            to_remove = []
            for oid in list(self.disappeared.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    to_remove.append(oid)
            for oid in to_remove:
                self.deregister(oid)
            return self.objects

        input_centroids = []
        for (x1,y1,x2,y2) in rects:
            input_centroids.append((int((x1+x2)/2), int((y1+y2)/2)))

        if len(self.objects) == 0:
            for c in input_centroids:
                self.register(c)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # distance matrix
            D = []
            for oc in object_centroids:
                row = [math.hypot(oc[0]-ic[0], oc[1]-ic[1]) for ic in input_centroids]
                D.append(row)

            # greedy matching sorted by distance
            items = []
            for r in range(len(D)):
                for c in range(len(D[0])):
                    items.append((D[r][c], r, c))
            items.sort(key=lambda x: x[0])

            used_rows = set()
            used_cols = set()
            matches = []
            for dist, r, c in items:
                if r in used_rows or c in used_cols:
                    continue
                if dist > self.max_distance:
                    continue
                used_rows.add(r); used_cols.add(c)
                matches.append((r, c))

            unmatched_rows = set(range(len(object_centroids))) - set(r for r,_ in matches)
            unmatched_cols = set(range(len(input_centroids))) - set(c for _,c in matches)

            # update matched
            for r,c in matches:
                oid = object_ids[r]
                self.objects[oid] = input_centroids[c]
                self.disappeared[oid] = 0

            # mark unmatched existing as disappeared
            for r in unmatched_rows:
                oid = object_ids[r]
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self.deregister(oid)

            # register new
            for c in unmatched_cols:
                self.register(input_centroids[c])

        return self.objects

# ---------- YOLO model init ----------
print("Loading YOLO model (this may download weights)...")
model = YOLO(YOLO_WEIGHTS)

# ---------- Video setup ----------
cap0 = cv2.VideoCapture(CAM0)
cap1 = cv2.VideoCapture(CAM1)
cap0.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap0.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
cap1.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

# fallback black frame
BLACK = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)

if not cap0.isOpened():
    print(f"Warning: camera {CAM0} not opened, using black frame.")
if not cap1.isOpened():
    print(f"Warning: camera {CAM1} not opened, using black frame.")

tracker0 = CentroidTracker()
tracker1 = CentroidTracker()
counter0 = VehicleCounter()
counter1 = VehicleCounter()

# optional totals
total_passed0 = 0
total_passed1 = 0

state = 0
state_start = time.time()
send_serial(state)

print("Starting YOLO adaptive control (Road0 cam {}, Road1 cam {})".format(CAM0, CAM1))
print("Press 'q' to quit. '0'/'1' to force.")

def detect_and_count(frame, tracker, line_ratio=LINE_POS_RATIO, model=model):
    """
    Run YOLO detection -> filter vehicles -> update tracker -> count when centroid passes line.
    Returns: tracked_list ([(id,(cx,cy),bbox)]), new_count_int (int), annotated_frame
    """
    h, w = frame.shape[:2]
    # run detection
    results = model(frame, imgsz=IMG_SIZE, conf=CONF_THRESH, iou=IOU_THRESH, verbose=False)
    detections = []
    for r in results:
        if not hasattr(r, 'boxes') or r.boxes is None:
            continue
        for box in r.boxes:
            cls = int(box.cls.cpu().numpy()[0]) if hasattr(box, 'cls') else None
            if cls is None or cls not in VEHICLE_CLASS_IDS:
                continue
            xyxy = box.xyxy.cpu().numpy()[0]
            x1, y1, x2, y2 = map(int, xyxy.tolist())
            # optional size filter: skip tiny boxes
            if (x2-x1) * (y2-y1) < 400:   # skip tiny detections (tweak)
                continue
            detections.append((x1, y1, x2, y2))

    # update tracker
    current_objects = tracker.update(detections)   # id -> centroid

    # create mapping object_id -> bbox (nearest bbox center)
    bbox_centers = [(((b[0]+b[2])//2, (b[1]+b[3])//2), b) for b in detections]
    tracked_list = []
    for oid, centroid in current_objects.items():
        # find nearest bbox center
        best = None; bestd = None
        for (bc, b) in bbox_centers:
            d = math.hypot(bc[0]-centroid[0], bc[1]-centroid[1])
            if bestd is None or d < bestd:
                bestd = d; best = b
        tracked_list.append((oid, centroid, best))

    # counting logic: count if centroid crosses below the line and id not counted before
    new_count = 0
    line_y = int(h * line_ratio)
    for oid, centroid, bbox in tracked_list:
        cX, cY = centroid
        if oid not in tracker.counted_ids:
            # simple rule: if centroid is below line (passed) then count
            if cY > line_y:
                tracker.counted_ids.add(oid)
                new_count += 1

    # annotate frame
    ann = frame.copy()
    cv2.line(ann, (0, line_y), (w, line_y), (0, 255, 255), 2)
    for oid, centroid, bbox in tracked_list:
        cX, cY = centroid
        if bbox is not None:
            x1,y1,x2,y2 = bbox
            cv2.rectangle(ann, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(ann, f"ID{oid}", (cX-10, cY-10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1)
        cv2.circle(ann, (cX, cY), 3, (0,0,255), -1)

    return tracked_list, new_count, ann

# ---------- Main loop ----------
while True:
    ret0, frame0 = cap0.read()
    ret1, frame1 = cap1.read()
    if not ret0:
        frame0 = BLACK.copy()
    else:
        if (frame0.shape[1], frame0.shape[0]) != (FRAME_WIDTH, FRAME_HEIGHT):
            frame0 = cv2.resize(frame0, (FRAME_WIDTH, FRAME_HEIGHT))
    if not ret1:
        frame1 = BLACK.copy()
    else:
        if (frame1.shape[1], frame1.shape[0]) != (FRAME_WIDTH, FRAME_HEIGHT):
            frame1 = cv2.resize(frame1, (FRAME_WIDTH, FRAME_HEIGHT))

    # detection + tracking + counting
    tracked0, inc0, ann0 = detect_and_count(frame0, tracker0, line_ratio=LINE_POS_RATIO, model=model)
    tracked1, inc1, ann1 = detect_and_count(frame1, tracker1, line_ratio=LINE_POS_RATIO, model=model)

    # update totals & moving average counters
    total_passed0 += inc0
    total_passed1 += inc1
    cnt0 = len(tracked0)
    cnt1 = len(tracked1)
    counter0.push(cnt0)
    counter1.push(cnt1)
    avg0 = counter0.avg()
    avg1 = counter1.avg()

    # decide switching using the same logic you had
    elapsed = time.time() - state_start
    current_avg = avg0 if state == 0 else avg1
    other_avg = avg1 if state == 0 else avg0

    do_switch = False
    if elapsed < MIN_GREEN:
        do_switch = False
    else:
        if other_avg > current_avg + HYSTERESIS:
            do_switch = True
        if elapsed >= MAX_GREEN:
            do_switch = True

    if do_switch:
        state = 1 - state
        state_start = time.time()
        print(f"Switching -> Road{state} GREEN | avg: r0={avg0:.2f}, r1={avg1:.2f} | totals: r0={total_passed0}, r1={total_passed1}")
        send_serial(state)

    # choose frames to display (annotated)
    frame0_display = ann0
    frame1_display = ann1

    # Overlay some status
    cv2.putText(frame0_display, f"Road0: {'GREEN' if state==0 else 'RED'}  cnt={cnt0} avg={avg0:.1f}", (10,25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
    cv2.putText(frame1_display, f"Road1: {'GREEN' if state==1 else 'RED'}  cnt={cnt1} avg={avg1:.1f}", (10,25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

    try:
        combined = cv2.hconcat([frame0_display, frame1_display])
    except:
        combined = np.hstack((cv2.resize(frame0_display, (FRAME_WIDTH, FRAME_HEIGHT)),
                              cv2.resize(frame1_display, (FRAME_WIDTH, FRAME_HEIGHT))))

    cv2.putText(combined, f"Elapsed: {int(elapsed)}s  Totals -> {total_passed0}/{total_passed1}", (10, combined.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230,230,230), 1)

    if SHOW_WINDOWS:
        cv2.imshow("Adaptive YOLO Traffic - Road0 | Road1", combined)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key == ord('0'):
        state = 0; state_start = time.time(); send_serial(state); print("Manual -> Road0 GREEN")
    if key == ord('1'):
        state = 1; state_start = time.time(); send_serial(state); print("Manual -> Road1 GREEN")
    if key == ord('r'):
        # reset trackers / counts
        tracker0 = CentroidTracker(); tracker1 = CentroidTracker()
        total_passed0 = total_passed1 = 0
        counter0 = VehicleCounter(); counter1 = VehicleCounter()
        print("Reset trackers & counters")

# cleanup
cap0.release()
cap1.release()
cv2.destroyAllWindows()
if ser:
    ser.close()
