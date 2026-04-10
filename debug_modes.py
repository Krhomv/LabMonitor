import serial
import time
import json
import os
import sys

def get_port():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            try:
                config = json.load(f)
                port = config.get("owon_port", "COM4")
                if port and port != "Simulated":
                    return port
            except:
                pass
    return "COM4"

PORT = get_port()
BAUD = 115200

def main():
    print(f"Starting mode discovery on {PORT}...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.5)
        seen_modes = set()
        
        with open("modes_log.txt", "w") as log:
            log.write(f"--- Mode Discovery Log for {PORT} ---\n")
            
        while True:
            ser.reset_input_buffer()
            ser.write(b"FUNC?\n")
            time.sleep(0.1)
            raw_mode = ser.readline().decode('ascii', errors='ignore').strip()
            
            if raw_mode:
                clean_mode = raw_mode.replace('"', '').strip()
                if clean_mode not in seen_modes:
                    seen_modes.add(clean_mode)
                    msg = f"NEW MODE DISCOVERED: '{clean_mode}' (Raw: {repr(raw_mode)})\n"
                    print(msg, end="")
                    with open("modes_log.txt", "a") as log:
                        log.write(msg)
            
            time.sleep(0.2)
            
    except Exception as e:
        with open("modes_log.txt", "a") as log:
            log.write(f"Error: {e}\n")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
