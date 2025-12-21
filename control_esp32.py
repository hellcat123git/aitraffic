import serial
import time

# CHANGE COM PORT HERE
ser = serial.Serial('COM5', 115200)   # use your COM port
time.sleep(2)  # wait for ESP32 reset

print("Connected to ESP32")

while True:
    ser.write(b"S1_GREEN\n")
    print("Signal 1 GREEN")
    time.sleep(5)

    ser.write(b"S2_GREEN\n")
    print("Signal 2 GREEN")
    time.sleep(5)

    ser.write(b"ALL_RED\n")
    print("ALL RED")
    time.sleep(3)
