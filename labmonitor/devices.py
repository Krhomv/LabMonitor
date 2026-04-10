import serial
import serial.tools.list_ports
import threading
import time

class DeviceBase:
    def __init__(self, name, baud):
        self.name = name
        self.baud = baud
        self.port = ""
        self.ser = None
        self.connected = False
        self.data = {}
        self.simulated = False
        self.is_communicating = False
        self.last_attempt = 0
        self._lock = threading.Lock()

    def connect(self, port):
        with self._lock:
            self.last_attempt = time.time()
            self.port = port
            if not port or port == "Simulated":
                self.simulated = True
                self.connected = True
                self.is_communicating = True
                print(f"[{self.name}] Started in Simulated mode.")
                return True
            try:
                self.ser = serial.Serial(port, self.baud, timeout=0.2, write_timeout=0.2)
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.connected = True
                self.simulated = False
                self.is_communicating = False
                print(f"[{self.name}] Connected to {port} at {self.baud} baud.")
                return True
            except Exception as e:
                print(f"[{self.name}] Connection Error on {port}: {e}")
                self.connected = False
                return False

    def disconnect(self):
        with self._lock:
            if self.ser:
                try:
                    self.ser.close()
                    print(f"[{self.name}] Disconnected.")
                except:
                    pass
            self.connected = False
            self.is_communicating = False

class OwonDevice(DeviceBase):
    def __init__(self):
        super().__init__("Owon XDM1041", 115200)
        self.data = {"value": " 0.0000", "unit": "VDC", "mode": "VOLT", "raw_float": 0.0}
        self._last_mode = ""
        self.modes = {
            "VOLT": "V-DC", "VOLT AC": "V-AC", 
            "CURR": "A-DC", "CURR AC": "A-AC", 
            "RES": "OHM", "CONT": "CONT", "DIOD": "DIOD", 
            "CAP": "CAP", "FREQ": "FREQ", "TEMP": "TEMP"
        }

    def format_value(self, raw, mode):
        try:
            val = float(raw)
            self.data["raw_float"] = val
            
            # Check for Overload (Open Circuit)
            if val >= 1e9 and ("RES" in mode or "CONT" in mode or "DIOD" in mode):
                return "   OL  ", self._get_base_unit(mode)
                
            if abs(val) < 1e-12: 
                val = 0.0
            
            unit = self._get_base_unit(mode)
            out_val = ""
            
            # Auto-Scale
            if "RES" in mode or "CONT" in mode:
                if val >= 1e6: val, unit = val/1e6, "MΩ"
                elif val >= 1e3: val, unit = val/1e3, "kΩ"
            elif "VOLT" in mode or "DIOD" in mode:
                if 0 < abs(val) < 0.1: val, unit = val*1000, "mV"
            elif "CURR" in mode:
                if 0 < abs(val) < 0.001: val, unit = val*1e6, "uA"
                elif 0 < abs(val) < 1.0: val, unit = val*1000, "mA"
            elif "CAP" in mode:
                if 0 < val < 1e-6: val, unit = val*1e9, "nF"
                elif 0 < val < 1e-3: val, unit = val*1e6, "uF"
                else: val, unit = val*1e3, "mF"
            elif "FREQ" in mode:
                if val >= 1e6: val, unit = val/1e6, "MHz"
                elif val >= 1e3: val, unit = val/1e3, "kHz"

            # Strict 5-digit precision logic
            v_abs = abs(val)
            if v_abs >= 9999.95: out_val = f"{v_abs:.0f}"
            elif v_abs >= 999.995: out_val = f"{v_abs:.1f}"
            elif v_abs >= 99.9995: out_val = f"{v_abs:.2f}"
            elif v_abs >= 9.99995: out_val = f"{v_abs:.3f}"
            else: out_val = f"{v_abs:.4f}"

            if "." in out_val: out_val = out_val.ljust(6, "0")
            else: out_val = out_val.rjust(6, " ")

            return ("-" if val < 0 else " ") + out_val, unit
        except:
            return " 0.0000", self._get_base_unit(mode)

    def _get_base_unit(self, mode):
        if "VOLT" in mode or "DIOD" in mode: return "V"
        if "CURR" in mode: return "A"
        if "RES" in mode or "CONT" in mode: return "Ω"
        if "CAP" in mode: return "F"
        if "FREQ" in mode: return "Hz"
        if "TEMP" in mode: return "°C"
        return ""

    def update(self):
        if not self.connected: return
        if self.simulated:
            import random
            self.data["mode"] = "VOLT"
            self.data["value"], self.data["unit"] = self.format_value(str(random.uniform(11.9, 12.1)), "VOLT")
            self.is_communicating = True
            return
        
        try:
            with self._lock:
                self.ser.reset_input_buffer()
                self.ser.write(b"FUNC?\n")
                mode_resp = self.ser.readline().decode('ascii', errors='ignore').strip()
                if mode_resp:
                    new_mode = mode_resp.replace('"', '').upper()
                    if new_mode != self._last_mode:
                        self.data["value"] = " 0.0000"
                        self._last_mode = new_mode
                    self.data["mode"] = new_mode
                
                self.ser.write(b"MEAS?\n")
                res = self.ser.readline().decode('ascii', errors='ignore').strip()
                if res:
                    parts = res.split(',')
                    self.data["value"], self.data["unit"] = self.format_value(parts[0], self.data["mode"])
                    self.is_communicating = True
                else:
                    self.is_communicating = False
        except:
            self.is_communicating = False
            self.disconnect()

    def test_connection(self, port):
        if port == "Simulated": return True
        try:
            with serial.Serial(port, 115200, timeout=0.5) as s:
                s.write(b"*IDN?\n")
                res = s.readline().decode('ascii', errors='ignore').strip()
                return "OWON" in res.upper() or "XDM1041" in res.upper()
        except:
            return False

class KoradDevice(DeviceBase):
    def __init__(self):
        super().__init__("Korad KA3005PS", 9600)
        self.data = {"v_out": "0.00", "i_out": "0.000", "v_set": "0.00", "i_set": "0.000", "output": False, "ocp": False, "ovp": False, "watts": "0.00", "mode": "CV"}

    def update(self):
        if not self.connected: return
        if self.simulated:
            import random
            v = random.uniform(11.9, 12.1); i = random.uniform(0.5, 0.6)
            self.data.update({
                "v_out": f"{v:05.2f}", "i_out": f"{i:05.3f}", 
                "v_set": f"{12.0:05.2f}", "i_set": f"{1.0:05.3f}",
                "watts": f"{v*i:.2f}", "output": True, "mode": "CV", "ocp": True, "ovp": False
            })
            self.is_communicating = True; return
        try:
            with self._lock:
                self.ser.reset_input_buffer()
                def q(cmd, l=None):
                    self.ser.write(cmd.encode()); time.sleep(0.05)
                    return self.ser.read(l).decode('ascii', errors='ignore').strip() if l else self.ser.read(1)
                v = q("VOUT1?", 5); i = q("IOUT1?", 5); vs = q("VSET1?", 5); is_ = q("ISET1?", 5); sb = q("STATUS?")
                try:
                    if v: self.data["v_out"] = f"{float(v):05.2f}"
                    if i: self.data["i_out"] = f"{float(i):05.3f}"
                    if vs: self.data["v_set"] = f"{float(vs):05.2f}"
                    if is_: self.data["i_set"] = f"{float(is_):05.3f}"
                    self.data["watts"] = f"{float(self.data['v_out']) * float(self.data['i_out']):.2f}"
                except: pass
                if sb:
                    s = ord(sb); self.data["mode"] = "CV" if (s & 0x01) else "CC"; self.data["ocp"] = bool(s & 0x20); self.data["output"] = bool(s & 0x40); self.data["ovp"] = bool(s & 0x80); self.is_communicating = True
                else: self.is_communicating = False
        except: 
            self.is_communicating = False
            self.disconnect()

    def test_connection(self, port):
        if port == "Simulated": return True
        try:
            with serial.Serial(port, 9600, timeout=0.5) as s:
                s.write(b"*IDN?"); res = s.read(30).decode('ascii', errors='ignore').strip()
                return "KORAD" in res.upper() or "KA3005" in res.upper()
        except: return False
