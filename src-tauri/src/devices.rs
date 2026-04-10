use serde::{Deserialize, Serialize};
use serialport::SerialPort;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct OwonData {
    pub value: String,
    pub unit: String,
    pub mode: String,
    pub raw_float: f64,
    pub connected: bool,
    pub is_communicating: bool,
}

impl Default for OwonData {
    fn default() -> Self {
        Self {
            value: " 0.0000".to_string(),
            unit: "VDC".to_string(),
            mode: "VOLT".to_string(),
            raw_float: 0.0,
            connected: false,
            is_communicating: false,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct KoradData {
    pub v_out: String,
    pub i_out: String,
    pub v_set: String,
    pub i_set: String,
    pub output: bool,
    pub ocp: bool,
    pub ovp: bool,
    pub watts: String,
    pub mode: String,
    pub connected: bool,
    pub is_communicating: bool,
}

impl Default for KoradData {
    fn default() -> Self {
        Self {
            v_out: "0.000".to_string(),
            i_out: "0.000".to_string(),
            v_set: "0.000".to_string(),
            i_set: "0.000".to_string(),
            output: false,
            ocp: false,
            ovp: false,
            watts: "0.00".to_string(),
            mode: "CV".to_string(),
            connected: false,
            is_communicating: false,
        }
    }
}

pub struct DeviceState {
    pub owon: Mutex<OwonData>,
    pub korad: Mutex<KoradData>,
}

impl Default for DeviceState {
    fn default() -> Self {
        Self {
            owon: Mutex::new(OwonData::default()),
            korad: Mutex::new(KoradData::default()),
        }
    }
}

fn get_base_unit(mode: &str) -> &'static str {
    if mode.contains("VOLT") || mode.contains("DIOD") { return "V"; }
    if mode.contains("CURR") { return "A"; }
    if mode.contains("RES") || mode.contains("CONT") { return "Ω"; }
    if mode.contains("CAP") { return "F"; }
    if mode.contains("FREQ") { return "Hz"; }
    if mode.contains("TEMP") { return "°C"; }
    ""
}

fn format_owon_value(raw: &str, mode: &str) -> (String, String, f64) {
    let mut val = raw.parse::<f64>().unwrap_or(0.0);
    let mut unit = get_base_unit(mode);

    if val.abs() >= 1e9 {
        return ("   OL  ".to_string(), unit.to_string(), val);
    }
    if val.abs() < 1e-12 {
        val = 0.0;
    }

    if mode.contains("RES") || mode.contains("CONT") {
        if val >= 1e6 { val /= 1e6; unit = "MΩ"; }
        else if val >= 1e3 { val /= 1e3; unit = "kΩ"; }
    } else if mode.contains("VOLT") || mode.contains("DIOD") {
        if val.abs() > 0.0 && val.abs() < 0.1 { val *= 1000.0; unit = "mV"; }
    } else if mode.contains("CURR") {
        if val.abs() > 0.0 && val.abs() < 0.001 { val *= 1e6; unit = "uA"; }
        else if val.abs() > 0.0 && val.abs() < 1.0 { val *= 1000.0; unit = "mA"; }
    } else if mode.contains("CAP") {
        if val > 0.0 && val < 1e-6 { val *= 1e9; unit = "nF"; }
        else if val > 0.0 && val < 1e-3 { val *= 1e6; unit = "uF"; }
        else if val >= 1e-3 { val *= 1e3; unit = "mF"; }
    } else if mode.contains("FREQ") {
        if val >= 1e6 { val /= 1e6; unit = "MHz"; }
        else if val >= 1e3 { val /= 1e3; unit = "kHz"; }
    }

    let v_abs = val.abs();
    if v_abs >= 99999.5 {
        return ("   OL  ".to_string(), unit.to_string(), val);
    }
    
    let mut out_val = if v_abs >= 9999.95 { format!("{:.0}", v_abs) }
    else if v_abs >= 999.995 { format!("{:.1}", v_abs) }
    else if v_abs >= 99.9995 { format!("{:.2}", v_abs) }
    else if v_abs >= 9.99995 { format!("{:.3}", v_abs) }
    else { format!("{:.4}", v_abs) };

    if out_val.contains('.') {
        while out_val.len() < 6 { out_val.push('0'); }
    } else {
        while out_val.len() < 6 { out_val.insert(0, ' '); }
    }

    let is_zero = out_val.chars().all(|c| c == '0' || c == '.' || c == ' ');
    let sign = if val < 0.0 && !is_zero { "-" } else { " " };
    (format!("{}{}", sign, out_val), unit.to_string(), val)
}

pub fn spawn_owon_thread(state: Arc<DeviceState>, config_port: Arc<Mutex<String>>) {
    thread::spawn(move || {
        let mut port_name = "".to_string();
        let mut port_opts: Option<Box<dyn SerialPort>> = None;
        let mut simulated = false;
        let mut last_attempt = Instant::now() - Duration::from_secs(10);
        let mut last_mode = String::new();
        let mut meas_count = 0;

        loop {
            let current_config_port = config_port.lock().unwrap().clone();
            if current_config_port != port_name {
                port_name = current_config_port.clone();
                port_opts = None;
                simulated = port_name == "Simulated";
                last_attempt = Instant::now() - Duration::from_secs(10);
                let mut data = state.owon.lock().unwrap();
                data.connected = false;
                data.is_communicating = false;
            }

            if port_name.is_empty() {
                thread::sleep(Duration::from_millis(500));
                continue;
            }

            if simulated {
                let mut data = state.owon.lock().unwrap();
                data.connected = true;
                data.is_communicating = true;
                data.mode = "VOLT".to_string();
                let val = (rand::random::<f64>() * 0.2) + 11.9;
                let formatted = format_owon_value(&val.to_string(), "VOLT");
                data.value = formatted.0;
                data.unit = formatted.1;
                data.raw_float = val;
                thread::sleep(Duration::from_millis(500));
                continue;
            }

            if port_opts.is_none() {
                if last_attempt.elapsed().as_secs() >= 1 {
                    last_attempt = Instant::now();
                    match serialport::new(&port_name, 115_200)
                        .timeout(Duration::from_millis(200))
                        .open() {
                        Ok(p) => {
                            let _ = p.clear(serialport::ClearBuffer::All);
                            port_opts = Some(p);
                            state.owon.lock().unwrap().connected = true;
                        }
                        Err(_) => {
                            let mut data = state.owon.lock().unwrap();
                            data.connected = false;
                            data.is_communicating = false;
                        }
                    }
                }
            } else {
                let p = port_opts.as_mut().unwrap();

                let query = |p: &mut Box<dyn SerialPort>, cmd: &str| -> Result<String, std::io::Error> {
                    let _ = p.clear(serialport::ClearBuffer::Input);
                    if let Err(e) = p.write_all(cmd.as_bytes()) {
                        return Err(e);
                    }
                    let mut resp = String::new();
                    let mut buf = [0u8; 128];
                    let start = Instant::now();
                    while start.elapsed() < Duration::from_millis(250) {
                        let read_success = match p.read(&mut buf) {
                            Ok(len) if len > 0 => {
                                resp.push_str(&String::from_utf8_lossy(&buf[..len]));
                                if resp.contains('\n') {
                                    break;
                                }
                                true
                            }
                            Ok(_) => false,
                            Err(_) => false,
                        };
                        if !read_success {
                            thread::sleep(Duration::from_millis(5));
                        }
                    }
                    Ok(resp.trim().to_string())
                };

                let mut write_failed = false;

                if meas_count >= 5 {
                    match query(p, "FUNC?\n") {
                        Ok(resp_mode) => {
                            let mut data = state.owon.lock().unwrap();
                            let resp_mode = resp_mode.replace("\"", "").to_uppercase();
                            if !resp_mode.is_empty() {
                                if resp_mode != last_mode {
                                    data.value = " 0.0000".to_string();
                                    last_mode = resp_mode.clone();
                                }
                                data.mode = resp_mode;
                                data.is_communicating = true;
                            } else {
                                data.is_communicating = false;
                            }
                        }
                        Err(_) => write_failed = true,
                    }
                    meas_count = 0;
                } else {
                    match query(p, "MEAS?\n") {
                        Ok(resp_meas) => {
                            let mut data = state.owon.lock().unwrap();
                            if !resp_meas.is_empty() {
                                let parts: Vec<&str> = resp_meas.split(',').collect();
                                let formatted = format_owon_value(parts[0], &data.mode);
                                data.value = formatted.0;
                                data.unit = formatted.1;
                                data.raw_float = formatted.2;
                                data.is_communicating = true;
                            } else {
                                data.is_communicating = false;
                            }
                        }
                        Err(_) => write_failed = true,
                    }
                    meas_count += 1;
                }

                if write_failed {
                    port_opts = None; // Force reconnect only on write failure
                    let mut data = state.owon.lock().unwrap();
                    data.is_communicating = false;
                }
            }
            thread::sleep(Duration::from_millis(150));
        }
    });
}

pub fn spawn_korad_thread(state: Arc<DeviceState>, config_port: Arc<Mutex<String>>) {
    thread::spawn(move || {
        let mut port_name = "".to_string();
        let mut port_opts: Option<Box<dyn SerialPort>> = None;
        let mut simulated = false;
        let mut last_attempt = Instant::now() - Duration::from_secs(10);

        loop {
            let current_config_port = config_port.lock().unwrap().clone();
            if current_config_port != port_name {
                port_name = current_config_port.clone();
                port_opts = None;
                simulated = port_name == "Simulated";
                last_attempt = Instant::now() - Duration::from_secs(10);
                let mut data = state.korad.lock().unwrap();
                data.connected = false;
                data.is_communicating = false;
            }

            if port_name.is_empty() {
                thread::sleep(Duration::from_millis(500));
                continue;
            }

            if simulated {
                let mut data = state.korad.lock().unwrap();
                data.connected = true;
                data.is_communicating = true;
                let v = (rand::random::<f64>() * 0.2) + 11.9;
                let i = (rand::random::<f64>() * 0.1) + 0.5;
                data.v_out = format!("{:05.2}", v);
                data.i_out = format!("{:05.3}", i);
                data.v_set = format!("{:05.2}", 12.0);
                data.i_set = format!("{:05.3}", 1.0);
                data.watts = format!("{:.2}", v * i);
                data.output = true;
                data.mode = "CV".to_string();
                data.ocp = true;
                data.ovp = false;
                thread::sleep(Duration::from_millis(500));
                continue;
            }

            if port_opts.is_none() {
                if last_attempt.elapsed().as_secs() >= 1 {
                    last_attempt = Instant::now();
                    match serialport::new(&port_name, 9600)
                        .timeout(Duration::from_millis(200))
                        .open() {
                        Ok(p) => {
                            let _ = p.clear(serialport::ClearBuffer::All);
                            port_opts = Some(p);
                            state.korad.lock().unwrap().connected = true;
                        }
                        Err(_) => {
                            let mut data = state.korad.lock().unwrap();
                            data.connected = false;
                            data.is_communicating = false;
                        }
                    }
                }
            } else {
                let p = port_opts.as_mut().unwrap();
                let _ = p.clear(serialport::ClearBuffer::Input);

                let query = |p: &mut Box<dyn SerialPort>, cmd: &str, len: usize| -> Option<String> {
                    if let Err(_) = p.write_all(cmd.as_bytes()) {
                        return None;
                    }
                    thread::sleep(Duration::from_millis(50));
                    let mut buf = vec![0; len];
                    match p.read_exact(&mut buf) {
                        Ok(_) => Some(String::from_utf8_lossy(&buf).trim().to_string()),
                        Err(_) => None,
                    }
                };

                let query_byte = |p: &mut Box<dyn SerialPort>, cmd: &str| -> Option<u8> {
                    if let Err(_) = p.write_all(cmd.as_bytes()) {
                        return None;
                    }
                    thread::sleep(Duration::from_millis(50));
                    let mut buf = [0u8; 1];
                    match p.read_exact(&mut buf) {
                        Ok(_) => Some(buf[0]),
                        Err(_) => None,
                    }
                };

                if let (Some(v), Some(i), Some(vs), Some(is_), Some(sb)) = (
                    query(p, "VOUT1?", 5),
                    query(p, "IOUT1?", 5),
                    query(p, "VSET1?", 5),
                    query(p, "ISET1?", 5),
                    query_byte(p, "STATUS?")
                ) {
                    let mut data = state.korad.lock().unwrap();
                    if let Ok(vf) = v.parse::<f64>() { data.v_out = format!("{:05.2}", vf); }
                    if let Ok(if_) = i.parse::<f64>() { data.i_out = format!("{:05.3}", if_); }
                    if let Ok(vsf) = vs.parse::<f64>() { data.v_set = format!("{:05.2}", vsf); }
                    if let Ok(isf) = is_.parse::<f64>() { data.i_set = format!("{:05.3}", isf); }
                    
                    if let (Ok(vf), Ok(if_)) = (data.v_out.parse::<f64>(), data.i_out.parse::<f64>()) {
                        data.watts = format!("{:.2}", vf * if_);
                    }

                    data.mode = if (sb & 0x01) != 0 { "CV".to_string() } else { "CC".to_string() };
                    data.ocp = (sb & 0x20) != 0;
                    data.output = (sb & 0x40) != 0;
                    data.ovp = (sb & 0x80) != 0;
                    data.is_communicating = true;
                } else {
                    let mut data = state.korad.lock().unwrap();
                    data.is_communicating = false;
                    port_opts = None; // Force reconnect
                }
            }
            thread::sleep(Duration::from_millis(150));
        }
    });
}
