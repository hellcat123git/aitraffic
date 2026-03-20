import serial
import time

class ArduinoBridge:
    def __init__(self, port=None, baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.simulation_mode = True if port is None else False
        
        if not self.simulation_mode:
            try:
                self.ser = serial.Serial(self.port, self.baud, timeout=1)
                time.sleep(2) # Give it time to initialize
                print(f"Connected to Arduino on {self.port}")
            except Exception as e:
                print(f"Failed to connect to Arduino: {e}. Switching to simulation mode.")
                self.simulation_mode = True
                
    def send(self, command):
        """
        Sends a command to the Arduino.
        Example: "R1_GREEN", "R2_RED"
        """
        if self.simulation_mode:
            print(f"[SIMULATION] Sending to Arduino: {command}")
        else:
            try:
                self.ser.write((command + "\n").encode())
                self.ser.flush()
            except Exception as e:
                print(f"Error sending to Arduino: {e}")
                
    def close(self):
        if not self.simulation_mode and self.ser:
            self.ser.close()
