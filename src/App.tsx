import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface AppConfig {
  owon_port: string;
  korad_port: string;
  bg_color: string;
  font_color: string;
  accent_color: string;
}

interface OwonData {
  value: string;
  unit: string;
  mode: string;
  raw_float: number;
  connected: boolean;
  is_communicating: boolean;
}

interface KoradData {
  v_out: string;
  i_out: string;
  v_set: string;
  i_set: string;
  output: boolean;
  ocp: boolean;
  ovp: boolean;
  watts: string;
  mode: string;
  connected: boolean;
  is_communicating: boolean;
}

interface DevicesState {
  owon: OwonData;
  korad: KoradData;
}

function App() {
  const [config, setConfig] = useState<AppConfig>({
    owon_port: "", korad_port: "", bg_color: "#0f0f0f", font_color: "#00ff41", accent_color: "#2196f3"
  });
  const [state, setState] = useState<DevicesState | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [ports, setPorts] = useState<string[]>([]);

  useEffect(() => {
    invoke<AppConfig>("get_config").then(setConfig).catch(console.error);

    const interval = setInterval(async () => {
      try {
        const res = await invoke<DevicesState>("get_devices_state");
        setState(res);
      } catch (e) {
        console.error(e);
      }
    }, 150);

    return () => clearInterval(interval);
  }, []);

  const refreshPorts = async () => {
    try {
      const p = await invoke<string[]>("get_serial_ports");
      setPorts(p);
    } catch (e) {
      console.error(e);
    }
  };

  const openSettings = () => {
    refreshPorts();
    setShowSettings(true);
  };

  const saveConfig = async () => {
    try {
      await invoke("save_config", { newConfig: config });
      setShowSettings(false);
    } catch (e) {
      console.error(e);
    }
  };

  const owon = state?.owon;
  const korad = state?.korad;

  if (!state) return <div className="loading" style={{ backgroundColor: config.bg_color }}>Connecting...</div>;

  const modeLabels: Record<string, string> = {
    "VOLT": "VDC", "VOLT AC": "VAC", "CURR": "ADC", "CURR AC": "AAC", 
    "RES": "OHM", "CONT": "CNT", "DIOD": "DIO", "CAP": "CAP", "FREQ": "FRQ", "TEMP": "TMP"
  };

  const modesPart1 = ["VOLT", "VOLT AC", "CURR", "CURR AC", "RES"];
  const modesPart2 = ["CONT", "DIOD", "CAP", "FREQ", "TEMP"];

  return (
    <div className="container" style={{ backgroundColor: config.bg_color, color: config.font_color }}>
      {showSettings ? (
        <div className="settings-panel">
          <h2 style={{ color: config.accent_color }}>CONFIGURATION</h2>
          <div className="settings-section">
            <div className="settings-header">
              <span>Devices</span>
              <button onClick={refreshPorts}>↻</button>
            </div>
            <div className="settings-row">
              <label>Owon Port</label>
              <select value={config.owon_port} onChange={e => setConfig({...config, owon_port: e.target.value})}>
                <option value="">Select...</option>
                {ports.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div className="settings-row">
              <label>Korad Port</label>
              <select value={config.korad_port} onChange={e => setConfig({...config, korad_port: e.target.value})}>
                <option value="">Select...</option>
                {ports.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          
          <div className="settings-section">
            <div className="settings-header"><span>Appearance</span></div>
            <div className="settings-row">
              <label>BG Color</label>
              <input type="text" value={config.bg_color} onChange={e => setConfig({...config, bg_color: e.target.value})} />
            </div>
            <div className="settings-row">
              <label>Font Color</label>
              <input type="text" value={config.font_color} onChange={e => setConfig({...config, font_color: e.target.value})} />
            </div>
          </div>

          <div className="settings-actions">
            <button className="save-btn" style={{ backgroundColor: config.accent_color }} onClick={saveConfig}>SAVE & APPLY</button>
            <button className="cancel-btn" onClick={() => setShowSettings(false)}>CANCEL</button>
          </div>
        </div>
      ) : (
        <div className="main-panel">
          <div className="header">
            <div className="title">DASHBOARD</div>
            <button className="settings-btn" onClick={openSettings}>⚙</button>
          </div>

          <div className="card">
            <div className="card-header">
              <div className={`indicator ${owon?.is_communicating ? 'on' : 'off'}`}></div>
              <span>MULTIMETER</span>
              <div className="line"></div>
            </div>

            <div className="modes-grid">
              <div className="modes-row">
                {modesPart1.map(m => (
                  <div key={m} className={`mode-chip ${owon?.mode === m ? 'active' : ''}`} style={owon?.mode === m ? { borderColor: config.accent_color, backgroundColor: `${config.accent_color}33`} : {}}>
                    {modeLabels[m] || m}
                  </div>
                ))}
              </div>
              <div className="modes-row">
                {modesPart2.map(m => (
                  <div key={m} className={`mode-chip ${owon?.mode === m ? 'active' : ''}`} style={owon?.mode === m ? { borderColor: config.accent_color, backgroundColor: `${config.accent_color}33`} : {}}>
                    {modeLabels[m] || m}
                  </div>
                ))}
              </div>
            </div>

            <div className="display-area">
              <div className="value-container">
                <span className="sign">{owon?.value ? owon.value.charAt(0) : " "}</span>
                <span className="value" style={{ 
                  color: (owon?.mode === "CONT" && owon.unit === "Ω" && owon.raw_float < 50.0) || 
                         (owon?.mode === "DIOD" && owon.unit === "V" && owon.raw_float < 0.2) ? "#ef4444" : config.font_color 
                }}>{owon?.value ? owon.value.slice(1) : "0.0000"}</span>
              </div>
              <div className="unit" style={{ 
                  color: (owon?.mode === "CONT" && owon.unit === "Ω" && owon.raw_float < 50.0) || 
                         (owon?.mode === "DIOD" && owon.unit === "V" && owon.raw_float < 0.2) ? "#ef4444" : config.font_color 
                }}>{owon?.unit || "VDC"}</div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <div className={`indicator ${korad?.is_communicating ? 'on' : 'off'}`}></div>
              <span>POWER SUPPLY</span>
              <div className="line"></div>
            </div>

            <div className="psu-badges">
              <div className="badges-left">
                <div className={`badge ${korad?.ovp ? 'alert' : ''}`}>OVP</div>
                <div className={`badge ${korad?.ocp ? 'alert' : ''}`}>OCP</div>
                <div className={`badge mode-badge ${korad?.mode === 'CC' ? 'cc' : 'cv'}`}>{korad?.mode || 'CV'}</div>
              </div>
              <div className={`status-badge ${korad?.output ? 'on' : 'off'}`}>
                {korad?.output ? "OUTPUT ON" : "OUTPUT OFF"}
              </div>
            </div>

            <div className="psu-display">
              <div className="psu-row">
                <div className="psu-set">{korad?.v_set || "0.000"} V</div>
                <div className="psu-val">{korad?.v_out || "0.000"} V</div>
              </div>
              <div className="psu-row">
                <div className="psu-set">{korad?.i_set || "0.000"} A</div>
                <div className="psu-val">{korad?.i_out || "0.000"} A</div>
              </div>
              <div className="psu-watts">
                {korad?.watts || "0.00"} W
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
