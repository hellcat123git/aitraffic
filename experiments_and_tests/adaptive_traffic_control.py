import cv2
import time
import serial
from ultralytics import YOLO

# ============== SETTINGS =================
CONFIDENCE = 0.4
VEHICLE_CLASSES = [2, 3, 5, 7]  # car, bike, bus, truck

CAM1 = 0
CAM2 = 1

SERIAL_PORT = "COM5"
BAUD = 115200

MIN_GREEN = 4        # faster minimum
MAX_GREEN = 15       # prevent long waits
YELLOW_TIME = 2
DIFF_THRESHOLD = 3   # faster intelligent switching
# ========================================

print("Loading YOLO...")
model = YOLO("yolov8n.pt")
print("YOLO ready")

# -------- Serial --------
ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
time.sleep(2)
print("Connected to ESP32")

def send(cmd):
    print(">>>", cmd)
    ser.write((cmd + "\n").encode())
    ser.flush()

# -------- Cameras --------
cap1 = cv2.VideoCapture(CAM1)
cap2 = cv2.VideoCapture(CAM2)

def count_vehicles(frame):
    results = model(frame, conf=CONFIDENCE, verbose=False)
    count = 0
    for box in results[0].boxes:
        if int(box.cls[0]) in VEHICLE_CLASSES:
            count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)
    return count, frame

def draw_signal(frame, text, color):
    cv2.putText(frame, f"SIGNAL: {text}",
                (10,80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2, color, 3)

# -------- INITIAL STATE --------
current = 1
signal1 = "GREEN"
signal2 = "RED"
send("R1_GREEN")
green_start = time.time()

# -------- MAIN LOOP --------
while True:
    r1, f1 = cap1.read()
    r2, f2 = cap2.read()
    if not r1 or not r2:
        continue

    c1, f1 = count_vehicles(f1)
    c2, f2 = count_vehicles(f2)

    elapsed = time.time() - green_start

    # -------- DECISION LOGIC --------
    if elapsed > MIN_GREEN:
        if current == 1:
            if (c2 - c1) >= DIFF_THRESHOLD or elapsed > MAX_GREEN:
                signal1 = "YELLOW"
                signal2 = "RED"
                send("R1_YELLOW")
                time.sleep(YELLOW_TIME)

                send("R2_GREEN")
                current = 2
                green_start = time.time()
                signal1 = "RED"
                signal2 = "GREEN"

        elif current == 2:
            if (c1 - c2) >= DIFF_THRESHOLD or elapsed > MAX_GREEN:
                signal2 = "YELLOW"
                signal1 = "RED"
                send("R2_YELLOW")
                time.sleep(YELLOW_TIME)

                send("R1_GREEN")
                current = 1
                green_start = time.time()
                signal2 = "RED"
                signal1 = "GREEN"

    # -------- DISPLAY --------
    cv2.putText(f1, f"Road 1 Vehicles: {c1}", (10,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    cv2.putText(f2, f"Road 2 Vehicles: {c2}", (10,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    draw_signal(
        f1,
        signal1,
        (0,255,0) if signal1 == "GREEN" else (0,255,255) if signal1 == "YELLOW" else (0,0,255)
    )
    draw_signal(
        f2,
        signal2,
        (0,255,0) if signal2 == "GREEN" else (0,255,255) if signal2 == "YELLOW" else (0,0,255)
    )

    cv2.imshow("Road 1", f1)
    cv2.imshow("Road 2", f2)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# -------- CLEANUP --------
send("ALL_RED")
cap1.release()
cap2.release()
cv2.destroyAllWindows()
ser.close()
