import serial
import time
import sys

PORT = "COM4"
BAUDS = [115200, 9600]
COMMANDS = [
    "*IDN?",
    ":SCPI:DISP?",
    ":MEAS?",
    "IDN?"
]
TERMINATORS = [b"\n", b"\r\n", b"\r"]

def run_debug():
    print(f"--- Owon XDM1041 Diagnostic on {PORT} ---")
    
    for baud in BAUDS:
        print(f"\n--- Testing Baud: {baud} ---")
        try:
            ser = serial.Serial(PORT, baud, timeout=1.0)
            
            for cmd in COMMANDS:
                for term in TERMINATORS:
                    full_cmd = cmd.encode() + term
                    print(f"Sending: {repr(full_cmd)}...", end=" ", flush=True)
                    
                    ser.reset_input_buffer()
                    ser.write(full_cmd)
                    time.sleep(0.2)
                    
                    response = ser.read_all()
                    if response:
                        print(f"SUCCESS! Response: {repr(response)}")
                    else:
                        print("Timeout (No response)")
            
            ser.close()
        except Exception as e:
            print(f"Could not open port: {e}")

if __name__ == "__main__":
    run_debug()
