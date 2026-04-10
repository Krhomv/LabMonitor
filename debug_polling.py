import serial
import time
import sys

PORT = "COM4" # Change if needed
BAUD = 115200
TIMEOUT = 0.5 # Wait up to 500ms for a response

def test_polling(delay_between_commands):
    print(f"\n--- Testing Polling with {delay_between_commands}s delay ---")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
        # Clear any lingering junk
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        success_count = 0
        timeout_count = 0
        
        for i in range(1, 11): # Try 10 polling cycles
            start_time = time.time()
            
            # 1. Poll Measurement
            ser.write(b"MEAS?\n")
            meas_res = ser.readline().decode().strip()
            
            time.sleep(delay_between_commands) # Delay before next command
            
            # 2. Poll Function
            ser.write(b"FUNC?\n")
            func_res = ser.readline().decode().strip()
            
            cycle_time = time.time() - start_time
            
            if meas_res and func_res:
                print(f"Cycle {i:02d}: {func_res} = {meas_res} (took {cycle_time:.3f}s)")
                success_count += 1
            else:
                print(f"Cycle {i:02d}: TIMEOUT/ERROR (MEAS: {repr(meas_res)}, FUNC: {repr(func_res)})")
                timeout_count += 1
                
                # If it freezes, try to clear buffers
                ser.reset_input_buffer()
            
            time.sleep(delay_between_commands) # Delay before next cycle
            
        ser.close()
        print(f"Result: {success_count} successes, {timeout_count} timeouts.")
        return success_count == 10
        
    except Exception as e:
        print(f"Error opening port: {e}")
        return False

if __name__ == "__main__":
    print("Starting Polling Rate Test for Owon XDM1041...")
    # Test aggressive polling first, then slow it down
    delays = [0.01, 0.05, 0.1, 0.25]
    
    for delay in delays:
        success = test_polling(delay)
        if success:
            print(f">>> SUCCESS! Delay {delay}s seems stable. <<<")
            break
        else:
            print(f">>> FAILED at delay {delay}s. The meter might be overwhelmed. <<<")
            time.sleep(2) # Give the meter a moment to recover before the next test
