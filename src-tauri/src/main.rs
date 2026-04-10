// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod devices;

use config::{AppConfig, ConfigManager};
use devices::{spawn_korad_thread, spawn_owon_thread, DeviceState, KoradData, OwonData};
use serde::Serialize;
use serialport::available_ports;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::State;

struct AppState {
    config_manager: Arc<ConfigManager>,
    device_state: Arc<DeviceState>,
    owon_port: Arc<Mutex<String>>,
    korad_port: Arc<Mutex<String>>,
}

#[derive(Serialize)]
struct DevicesStatePayload {
    owon: OwonData,
    korad: KoradData,
}

#[tauri::command]
fn get_config(state: State<AppState>) -> AppConfig {
    state.config_manager.config.lock().unwrap().clone()
}

#[tauri::command]
fn save_config(state: State<AppState>, new_config: AppConfig) -> Result<(), String> {
    {
        let mut cfg = state.config_manager.config.lock().unwrap();
        *cfg = new_config.clone();
    }
    
    // Update active ports
    *state.owon_port.lock().unwrap() = new_config.owon_port.clone();
    *state.korad_port.lock().unwrap() = new_config.korad_port.clone();

    state.config_manager.save()
}

#[tauri::command]
fn get_devices_state(state: State<AppState>) -> DevicesStatePayload {
    let owon = state.device_state.owon.lock().unwrap().clone();
    let korad = state.device_state.korad.lock().unwrap().clone();
    DevicesStatePayload { owon, korad }
}

#[tauri::command]
fn get_serial_ports() -> Vec<String> {
    let mut ports = vec![];
    if let Ok(available) = available_ports() {
        for port in available {
            ports.push(port.port_name);
        }
    }
    ports.push("Simulated".to_string());
    ports
}

#[tauri::command]
fn test_owon(state: State<AppState>, port: String) -> bool {
    if port.is_empty() { return false; }
    if port == "Simulated" {
        return true;
    }
    if *state.owon_port.lock().unwrap() == port && state.device_state.owon.lock().unwrap().is_communicating {
        return true;
    }
    if let Ok(mut p) = serialport::new(&port, 115_200)
        .timeout(Duration::from_millis(500))
        .open()
    {
        let _ = p.clear(serialport::ClearBuffer::All);
        if p.write_all(b"*IDN?\n").is_ok() {
            std::thread::sleep(Duration::from_millis(100));
            let mut buf = [0u8; 128];
            if let Ok(len) = p.read(&mut buf) {
                let res = String::from_utf8_lossy(&buf[..len]).to_uppercase();
                return res.contains("OWON") || res.contains("XDM1041");
            }
        }
    }
    false
}

#[tauri::command]
fn test_korad(state: State<AppState>, port: String) -> bool {
    if port.is_empty() { return false; }
    if port == "Simulated" {
        return true;
    }
    if *state.korad_port.lock().unwrap() == port && state.device_state.korad.lock().unwrap().is_communicating {
        return true;
    }
    if let Ok(mut p) = serialport::new(&port, 9600)
        .timeout(Duration::from_millis(500))
        .open()
    {
        let _ = p.clear(serialport::ClearBuffer::All);
        if p.write_all(b"*IDN?").is_ok() {
            std::thread::sleep(Duration::from_millis(100));
            let mut buf = [0u8; 128];
            if let Ok(len) = p.read(&mut buf) {
                let res = String::from_utf8_lossy(&buf[..len]).to_uppercase();
                return res.contains("KORAD") || res.contains("KA3005");
            }
        }
    }
    false
}

fn main() {
    let config_manager = Arc::new(ConfigManager::new());
    let init_cfg = config_manager.config.lock().unwrap().clone();
    
    let device_state = Arc::new(DeviceState::default());
    let owon_port = Arc::new(Mutex::new(init_cfg.owon_port.clone()));
    let korad_port = Arc::new(Mutex::new(init_cfg.korad_port.clone()));

    spawn_owon_thread(device_state.clone(), owon_port.clone());
    spawn_korad_thread(device_state.clone(), korad_port.clone());

    let state = AppState {
        config_manager,
        device_state,
        owon_port,
        korad_port,
    };

    tauri::Builder::default()
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            get_config,
            save_config,
            get_devices_state,
            get_serial_ports,
            test_owon,
            test_korad
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
