use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::Mutex;

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct AppConfig {
    pub owon_port: String,
    pub korad_port: String,
    pub bg_color: String,
    pub font_color: String,
    pub accent_color: String,
    pub device_bg_color: String,
    pub watts_color: String,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            owon_port: "".to_string(),
            korad_port: "".to_string(),
            bg_color: "#0f0f0f".to_string(),
            font_color: "#f97c02".to_string(),
            accent_color: "#2196f3".to_string(),
            device_bg_color: "#141414".to_string(),
            watts_color: "#fbbf24".to_string(),
        }
    }
}

pub struct ConfigManager {
    pub config: Mutex<AppConfig>,
    file_path: PathBuf,
}

impl ConfigManager {
    pub fn new() -> Self {
        #[cfg(debug_assertions)]
        let file_path = PathBuf::from("../config.json");
        #[cfg(not(debug_assertions))]
        let file_path = PathBuf::from("config.json");
        let config = if file_path.exists() {
            if let Ok(contents) = fs::read_to_string(&file_path) {
                serde_json::from_str(&contents).unwrap_or_default()
            } else {
                AppConfig::default()
            }
        } else {
            AppConfig::default()
        };

        Self {
            config: Mutex::new(config),
            file_path,
        }
    }

    pub fn save(&self) -> Result<(), String> {
        let config = self.config.lock().unwrap();
        let contents = serde_json::to_string_pretty(&*config).map_err(|e| e.to_string())?;
        fs::write(&self.file_path, contents).map_err(|e| e.to_string())?;
        Ok(())
    }
}
