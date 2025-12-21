import serial
import time

PORT = "COM5"   # 🔴 CHANGE if your ESP32 is on another COM
BAUD = 115200

print("Opening serial port...")
ser = serial.Serial(PORT, BAUD, timeout=1)

# ESP32 resets when serial opens
time.sleep(2)

print("Sending ON")
ser.write(b"ON\n")
time.sleep(3)

print("Sending OFF")
ser.write(b"OFF\n")

ser.close()
print("Done")
