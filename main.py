import flet as ft
import serial
import serial.tools.list_ports
import threading
import time
import json
import os
import traceback
import asyncio

CONFIG_FILE = "config.json"

class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {
            "owon_port": "",
            "korad_port": "",
            "bg_color": "#0f0f0f",
            "font_color": "#00ff41", # Matrix green
            "accent_color": "#2196f3"
        }

    @staticmethod
    def save(config):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)

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

            # Force exact 6-char width for the value part (excluding sign)
            # This prevents the unit from jumping horizontally.
            if "." in out_val: out_val = out_val.ljust(6, "0")
            else: out_val = out_val.rjust(6, " ")

            # Polarity stability: leading space or minus sign
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

def main(page: ft.Page):
    config = ConfigManager.load()
    page.title = "LabMonitor"
    page.bgcolor = config["bg_color"]; page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 400; page.window.height = 750; page.window.resizable = False; page.window.maximizable = False; page.padding = 15

    owon = OwonDevice(); korad = KoradDevice()
    
    app_running = [True]
    
    def window_event(e):
        if e.data == "close":
            app_running[0] = False
            try:
                owon.disconnect()
                korad.disconnect()
            except:
                pass
            
    page.on_window_event = window_event
    owon_ind = ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.RED_700)
    korad_ind = ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.RED_700)
    
    # Decoupled number and unit for Multimeter
    owon_sign = ft.Text(" ", size=60, weight="bold", color=config["font_color"], font_family="Consolas")
    owon_val = ft.Text("0.0000", size=60, weight="bold", color=config["font_color"], font_family="Consolas")
    owon_unit = ft.Text("VDC", size=20, color=config["font_color"], font_family="Consolas")

    mode_labels = {"VOLT":"VDC","VOLT AC":"VAC","CURR":"ADC","CURR AC":"AAC","RES":"OHM","CONT":"CNT","DIOD":"DIO","CAP":"CAP","FREQ":"FRQ","TEMP":"TMP"}
    mode_chips = []
    for raw, disp in owon.modes.items():
        mode_chips.append(ft.Container(
            content=ft.Text(mode_labels.get(raw, "???"), size=10, weight="bold"),
            padding=ft.padding.symmetric(horizontal=4, vertical=6),
            border_radius=4, border=ft.border.all(1, ft.Colors.GREY_800),
            data=raw, expand=True, alignment=ft.Alignment.CENTER
        ))

    mode_row_1 = ft.Row(mode_chips[:5], spacing=4, alignment="center")
    mode_row_2 = ft.Row(mode_chips[5:], spacing=4, alignment="center")

    psu_v = ft.Text("00.00 V", size=60, weight="bold", color=config["font_color"], font_family="Consolas")
    psu_a = ft.Text("0.000 A", size=60, weight="bold", color=config["font_color"], font_family="Consolas")
    psu_w = ft.Text("0.00 W", size=30, color=ft.Colors.AMBER_500, weight="bold")
    psu_v_set = ft.Text("00.00 V", size=18, color=ft.Colors.GREY_400, font_family="Consolas")
    psu_a_set = ft.Text("0.000 A", size=18, color=ft.Colors.GREY_400, font_family="Consolas")
    
    def mk_badge(t): return ft.Container(content=ft.Text(t, size=10, weight="bold"), padding=ft.padding.symmetric(horizontal=6, vertical=4), border_radius=4, border=ft.border.all(1, ft.Colors.GREY_900), bgcolor=ft.Colors.BLACK, alignment=ft.Alignment.CENTER)
    psu_mode_badge = mk_badge("CV")
    ovp_badge = mk_badge("OVP")
    ocp_badge = mk_badge("OCP")
    psu_stat = ft.Container(content=ft.Text("OFF", color=ft.Colors.BLACK, weight="bold", size=12), bgcolor=ft.Colors.RED_700, padding=6, border_radius=4, width=90, alignment=ft.Alignment.CENTER)

    def switch_view(to_settings):
        if to_settings: refresh_ports()
        top_container.content = settings_layout if to_settings else main_layout; page.update()

    def refresh_ports(e=None):
        ports = [p.device for p in serial.tools.list_ports.comports()] + ["Simulated"]
        owon_dd.options = [ft.dropdown.Option(p) for p in ports]
        korad_dd.options = [ft.dropdown.Option(p) for p in ports]
        # Ensure dropdowns show current selection
        owon_dd.value = config["owon_port"]; korad_dd.value = config["korad_port"]
        if e: page.update()

    async def update_loop():
        await asyncio.sleep(0.5); page.window.width = 401; page.update()
        await asyncio.sleep(0.1); page.window.width = 400; page.update()
        while app_running[0]:
            try:
                # Auto-reconnect logic
                now = time.time()
                if not owon.connected and config["owon_port"] and config["owon_port"] != "Simulated":
                    if now - owon.last_attempt >= 1.0:
                        await asyncio.to_thread(owon.connect, config["owon_port"])
                if not korad.connected and config["korad_port"] and config["korad_port"] != "Simulated":
                    if now - korad.last_attempt >= 1.0:
                        await asyncio.to_thread(korad.connect, config["korad_port"])

                if top_container.content == main_layout:
                    await asyncio.to_thread(owon.update); await asyncio.to_thread(korad.update)
                    
                    # Owon Logic
                    owon_ind.bgcolor = ft.Colors.GREEN_500 if owon.is_communicating else ft.Colors.RED_700
                    f_val = owon.data["value"]
                    owon_sign.value = f_val[0] if f_val else " "
                    owon_val.value = f_val[1:] if f_val else "0.0000"
                    owon_unit.value = owon.data["unit"]
                    cur_m = owon.data.get("mode", ""); base_c = config["font_color"]
                    raw_f = owon.data.get("raw_float", 0.0)
                    if cur_m == "CONT" and raw_f < 50.0 and owon.data["unit"] == "Ω": base_c = ft.Colors.RED_500
                    elif cur_m == "DIOD" and raw_f < 0.2 and owon.data["unit"] == "V": base_c = ft.Colors.RED_500
                    owon_val.color = owon_unit.color = base_c
                    for c in mode_chips:
                        if c.data == cur_m: c.bgcolor = ft.Colors.BLUE_900; c.border = ft.border.all(1, ft.Colors.BLUE_400)
                        else: c.bgcolor = ft.Colors.BLACK; c.border = ft.border.all(1, ft.Colors.GREY_900)
                    
                    # Korad Logic
                    korad_ind.bgcolor = ft.Colors.GREEN_500 if korad.is_communicating else ft.Colors.RED_700
                    psu_v.value = f"{korad.data['v_out']} V"; psu_a.value = f"{korad.data['i_out']} A"; psu_w.value = f"{korad.data['watts']} W"
                    psu_v_set.value = f"{korad.data['v_set']} V"; psu_a_set.value = f"{korad.data['i_set']} A"
                    
                    psu_mode_badge.content.value = korad.data["mode"]
                    if korad.data["mode"] == "CC": psu_mode_badge.bgcolor = ft.Colors.BLUE_900; psu_mode_badge.border = ft.border.all(1, ft.Colors.BLUE_400)
                    else: psu_mode_badge.bgcolor = ft.Colors.GREEN_900; psu_mode_badge.border = ft.border.all(1, ft.Colors.GREEN_400)
                    
                    if korad.data["ovp"]: ovp_badge.bgcolor = ft.Colors.RED_900; ovp_badge.border = ft.border.all(1, ft.Colors.RED_400)
                    else: ovp_badge.bgcolor = ft.Colors.BLACK; ovp_badge.border = ft.border.all(1, ft.Colors.GREY_900)
                        
                    if korad.data["ocp"]: ocp_badge.bgcolor = ft.Colors.RED_900; ocp_badge.border = ft.border.all(1, ft.Colors.RED_400)
                    else: ocp_badge.bgcolor = ft.Colors.BLACK; ocp_badge.border = ft.border.all(1, ft.Colors.GREY_900)

                    if korad.data["output"]: psu_stat.content.value = "OUTPUT ON"; psu_stat.bgcolor = ft.Colors.GREEN_700; psu_stat.border = ft.border.all(1, ft.Colors.GREEN_400)
                    else: psu_stat.content.value = "OUTPUT OFF"; psu_stat.bgcolor = ft.Colors.RED_700; psu_stat.border = None
                    page.update()
            except: pass
            await asyncio.sleep(0.15)

    def draw_h(title, ind):
        return ft.Row([ind, ft.Text(title, size=11, weight="bold", color=ft.Colors.GREY_600, margin=ft.margin.only(right=10)), ft.Container(height=1, bgcolor=ft.Colors.GREY_800, expand=True)], alignment="center")

    main_layout = ft.Column([
        ft.Row([ft.Text("DASHBOARD", size=10, weight="bold", color=ft.Colors.GREY_700), ft.IconButton(ft.Icons.SETTINGS, icon_size=16, on_click=lambda _: switch_view(True), padding=0)], alignment="spaceBetween"),
        ft.Container(content=ft.Column([
            draw_h("MULTIMETER", owon_ind), 
            mode_row_1, mode_row_2, 
            ft.Row([
                ft.Container(content=owon_sign, alignment=ft.Alignment.TOP_RIGHT, expand=True),
                ft.Column([
                    owon_val,
                    ft.Container(content=owon_unit, padding=ft.padding.only(top=-20))
                ], horizontal_alignment="end", spacing=0),
                ft.Container(expand=True)
            ], vertical_alignment="start", spacing=0)
        ], spacing=8), padding=15, border_radius=10, border=ft.border.all(1, ft.Colors.GREY_900), bgcolor=ft.Colors.BLACK45),
        ft.Container(height=5),
        ft.Container(content=ft.Column([
            draw_h("POWER SUPPLY", korad_ind), 
            ft.Row([ft.Row([ovp_badge, ocp_badge, psu_mode_badge], spacing=5), psu_stat], alignment="spaceBetween"), 
            ft.Column([
                ft.Column([psu_v_set, psu_v], horizontal_alignment="start", spacing=-18),
                ft.Column([psu_a_set, psu_a], horizontal_alignment="start", spacing=-18),
                ft.Row([psu_w], alignment="center")
            ], horizontal_alignment="center", spacing=5)
        ], spacing=10), padding=15, border_radius=10, border=ft.border.all(1, ft.Colors.GREY_900), bgcolor=ft.Colors.BLACK45),
    ], spacing=5)

    def save_s(e):
        config.update({"owon_port": owon_dd.value, "korad_port": korad_dd.value, "bg_color": bg_in.value, "font_color": font_in.value})
        ConfigManager.save(config); page.bgcolor = config["bg_color"]
        owon_sign.color = owon_val.color = owon_unit.color = psu_v.color = psu_a.color = config["font_color"]
        owon.disconnect(); korad.disconnect(); owon.connect(config["owon_port"]); korad.connect(config["korad_port"]); switch_view(False)
    
    def test_o(e):
        res = owon.test_connection(owon_dd.value); test_o_btn.text = "OK" if res else "FAIL"; test_o_btn.bgcolor = ft.Colors.GREEN_900 if res else ft.Colors.RED_900; page.update()
    def test_k(e):
        res = korad.test_connection(korad_dd.value); test_k_btn.text = "OK" if res else "FAIL"; test_k_btn.bgcolor = ft.Colors.GREEN_900 if res else ft.Colors.RED_900; page.update()

    inp_s = {"text_size": 12, "expand": True, "bgcolor": ft.Colors.GREY_900, "border_color": ft.Colors.GREY_700, "border_radius": 5, "color": ft.Colors.WHITE}
    btn_s = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4))
    
    owon_dd = ft.Dropdown(label="Owon Port", value=config["owon_port"], **inp_s); korad_dd = ft.Dropdown(label="Korad Port", value=config["korad_port"], **inp_s)
    test_o_btn = ft.ElevatedButton("TEST", on_click=test_o, bgcolor=ft.Colors.GREY_800, style=btn_s); test_k_btn = ft.ElevatedButton("TEST", on_click=test_k, bgcolor=ft.Colors.GREY_800, style=btn_s)
    bg_in = ft.TextField(label="BG Color", value=config["bg_color"], **inp_s); font_in = ft.TextField(label="Font Color", value=config["font_color"], **inp_s)
    
    settings_layout = ft.Container(
        content=ft.Column([
            ft.Text("CONFIGURATION", size=18, weight="bold", color=ft.Colors.BLUE_500),
            ft.Row([ft.Text("Devices", size=12, weight="bold", color=ft.Colors.GREY_500), ft.IconButton(ft.Icons.REFRESH, icon_size=14, on_click=refresh_ports)], alignment="spaceBetween"),
            ft.Row([owon_dd, test_o_btn]),
            ft.Row([korad_dd, test_k_btn]),
            ft.Text("Appearance", size=12, weight="bold", color=ft.Colors.GREY_500),
            ft.Row([bg_in, font_in]),
            ft.Row([
                ft.ElevatedButton("SAVE & APPLY", on_click=save_s, bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE, expand=True, style=btn_s),
                ft.ElevatedButton("CANCEL", on_click=lambda _: switch_view(False), expand=True, bgcolor=ft.Colors.GREY_800, color=ft.Colors.WHITE, style=btn_s)
            ])
        ], spacing=12),
        padding=ft.padding.only(left=20, top=20, right=20, bottom=10),
        border_radius=10, border=ft.border.all(1, ft.Colors.GREY_900), bgcolor=ft.Colors.BLACK45
    )

    top_container = ft.Container(content=main_layout)
    page.add(top_container)
    
    if config["owon_port"]:
        owon.connect(config["owon_port"])
    if config["korad_port"]:
        korad.connect(config["korad_port"])
        
    page.run_task(update_loop)

ft.run(main)
