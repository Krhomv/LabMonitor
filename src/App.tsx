import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface AppConfig {
  owon_port: string;
  korad_port: string;
  bg_color: string;
  font_color: string;
  accent_color: string;
  device_bg_color: string;
  watts_color: string;
  overlay_port: number;
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
    owon_port: "", korad_port: "", bg_color: "#0f0f0f", font_color: "#f97c02", accent_color: "#2196f3", device_bg_color: "#141414", watts_color: "#fbbf24", overlay_port: 8765
  });
  const [state, setState] = useState<DevicesState | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [ports, setPorts] = useState<string[]>([]);
  const [owonTest, setOwonTest] = useState<string | null>(null);
  const [koradTest, setKoradTest] = useState<string | null>(null);

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

  const ModeIcon = ({ mode }: { mode: string }) => {
    const s = { stroke: "currentColor", strokeWidth: 2.2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
    switch (mode) {
      case "VOLT": return ( // V⎓
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4 7 L 8 17 L 12 7" />
          <path d="M 15 10 H 22 M 15 14 H 16.5 M 17.75 14 H 19.25 M 20.5 14 H 22" />
        </svg>
      );
      case "VOLT AC": return ( // V~
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4 7 L 8 17 L 12 7" />
          <path d="M 15 12 Q 16.75 8.5 18.5 12 T 22 12" />
        </svg>
      );
      case "CURR": return ( // A⎓
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4 17 L 8 7 L 12 17 M 5.5 13 H 10.5" />
          <path d="M 15 10 H 22 M 15 14 H 16.5 M 17.75 14 H 19.25 M 20.5 14 H 22" />
        </svg>
      );
      case "CURR AC": return ( // A~
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4 17 L 8 7 L 12 17 M 5.5 13 H 10.5" />
          <path d="M 15 12 Q 16.75 8.5 18.5 12 T 22 12" />
        </svg>
      );
      case "RES": return ( // OHM
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4.5 17 H 8.5 C 7.5 15.5 7 13.5 7 11 A 5 5 0 1 1 17 11 C 17 13.5 16.5 15.5 15.5 17 H 19.5" />
        </svg>
      );
      case "CONT": return ( // CONT
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 9 12 A 0.5 0.5 0 1 1 8 12 A 0.5 0.5 0 1 1 9 12" fill="currentColor" stroke="none" />
          <path d="M 12 9.5 A 3.5 3.5 0 0 1 12 14.5" />
          <path d="M 15 7 A 7 7 0 0 1 15 17" />
          <path d="M 18 4.5 A 10.5 10.5 0 0 1 18 19.5" />
        </svg>
      );
      case "DIOD": return ( // DIOD
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 3 12 H 9 M 17 12 H 21" />
          <path d="M 9 7 L 17 12 L 9 17 Z" />
          <path d="M 17 7 V 17" />
        </svg>
      );
      case "CAP": return ( // CAP
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 10 6 V 18 M 14 6 V 18 M 4 12 H 10 M 14 12 H 20" />
        </svg>
      );
      case "FREQ": return ( // FREQ (Hz)
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 4 7 V 17 M 11 7 V 17 M 4 12 H 11" />
          <path d="M 14 11 H 20 L 14 17 H 20" />
        </svg>
      );
      case "TEMP": return ( // TEMP
        <svg width="24" height="24" viewBox="0 0 24 24" {...s}>
          <path d="M 10 14.5 V 6 A 2 2 0 0 1 14 6 V 14.5 A 4 4 0 1 1 10 14.5 Z" />
          <path d="M 12 11 V 17" />
        </svg>
      );
      default: return <span>{mode}</span>;
    }
  };

  const modeLabels: Record<string, React.ReactNode> = {
    "VOLT": <ModeIcon mode="VOLT" />, 
    "VOLT AC": <ModeIcon mode="VOLT AC" />, 
    "CURR": <ModeIcon mode="CURR" />, 
    "CURR AC": <ModeIcon mode="CURR AC" />, 
    "RES": <ModeIcon mode="RES" />, 
    "CONT": <ModeIcon mode="CONT" />, 
    "DIOD": <ModeIcon mode="DIOD" />, 
    "CAP": <ModeIcon mode="CAP" />, 
    "FREQ": <ModeIcon mode="FREQ" />, 
    "TEMP": <ModeIcon mode="TEMP" />
  };

  const modesPart1 = ["VOLT", "VOLT AC", "CURR", "CURR AC", "RES"];
  const modesPart2 = ["CONT", "DIOD", "CAP", "FREQ", "TEMP"];

  const isRedAlert = (owon?.mode === "CONT" && owon?.unit === "Ω" && (owon?.raw_float ?? 0) < 50.0) || 
                     (owon?.mode === "DIOD" && owon?.unit === "V" && (owon?.raw_float ?? 0) < 0.2);
  const activeFontColor = isRedAlert ? "#ef4444" : config.font_color;

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
              <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
                <select value={config.owon_port} onChange={e => setConfig({...config, owon_port: e.target.value})}>
                  <option value="">Select...</option>
                  {ports.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button 
                  className={`test-btn ${owonTest || ''}`}
                  onClick={async () => {
                    setOwonTest("testing");
                    try {
                      const ok = await invoke<boolean>("test_owon", { port: config.owon_port });
                      setOwonTest(ok ? "success" : "error");
                    } catch { setOwonTest("error"); }
                  }}
                >{owonTest === 'testing' ? 'PING...' : owonTest === 'success' ? 'OK' : owonTest === 'error' ? 'FAIL' : 'TEST'}</button>
              </div>
            </div>
            <div className="settings-row">
              <label>Korad Port</label>
              <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
                <select value={config.korad_port} onChange={e => setConfig({...config, korad_port: e.target.value})}>
                  <option value="">Select...</option>
                  {ports.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button 
                  className={`test-btn ${koradTest || ''}`}
                  onClick={async () => {
                    setKoradTest("testing");
                    try {
                      const ok = await invoke<boolean>("test_korad", { port: config.korad_port });
                      setKoradTest(ok ? "success" : "error");
                    } catch { setKoradTest("error"); }
                  }}
                >{koradTest === 'testing' ? 'PING...' : koradTest === 'success' ? 'OK' : koradTest === 'error' ? 'FAIL' : 'TEST'}</button>
              </div>
            </div>
          </div>
          
          <div className="settings-section">
            <div className="settings-header"><span>Appearance</span></div>
            <div className="settings-row">
              <label>BG Color</label>
              <input type="color" value={config.bg_color} onChange={e => setConfig({...config, bg_color: e.target.value})} style={{ padding: 0 }} />
            </div>
            <div className="settings-row">
              <label>Device BG Color</label>
              <input type="color" value={config.device_bg_color} onChange={e => setConfig({...config, device_bg_color: e.target.value})} style={{ padding: 0 }} />
            </div>
            <div className="settings-row">
              <label>Font Color</label>
              <input type="color" value={config.font_color} onChange={e => setConfig({...config, font_color: e.target.value})} style={{ padding: 0 }} />
            </div>
            <div className="settings-row">
              <label>Accent Color</label>
              <input type="color" value={config.accent_color} onChange={e => setConfig({...config, accent_color: e.target.value})} style={{ padding: 0 }} />
            </div>
            <div className="settings-row">
              <label>Watts Color</label>
              <input type="color" value={config.watts_color} onChange={e => setConfig({...config, watts_color: e.target.value})} style={{ padding: 0 }} />
            </div>
          </div>

          <div className="settings-section">
            <div className="settings-header"><span>OBS Overlay</span></div>
            <div className="settings-row">
              <label>Port</label>
              <input type="number" value={config.overlay_port} onChange={e => setConfig({...config, overlay_port: parseInt(e.target.value) || 8765})} style={{ width: 80 }} />
            </div>
            <div className="settings-row">
              <label>Multimeter</label>
              <button className="copy-btn" onClick={() => navigator.clipboard.writeText(`http://localhost:${config.overlay_port}/overlay/owon`)}>Copy URL</button>
            </div>
            <div className="settings-row">
              <label>Power Supply</label>
              <button className="copy-btn" onClick={() => navigator.clipboard.writeText(`http://localhost:${config.overlay_port}/overlay/korad`)}>Copy URL</button>
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

          <div className="card" style={{ backgroundColor: config.device_bg_color }}>
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
              <div className="value-container" style={{ textShadow: `0 0 15px ${activeFontColor}33`, color: activeFontColor }}>
                <span className="sign">{owon?.value ? owon.value.charAt(0) : " "}</span>
                <span className="value">{owon?.value ? owon.value.slice(1) : "0.0000"}</span>
              </div>
              <div className="unit" style={{ color: activeFontColor }}>{owon?.unit || "VDC"}</div>
            </div>
          </div>

          <div className="card" style={{ backgroundColor: config.device_bg_color }}>
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
              <div className={`badge ${korad?.output ? 'out-on' : ''}`}>
                {korad?.output ? "OUTPUT ON" : "OUTPUT OFF"}
              </div>
            </div>

            <div className="psu-display">
              <div className="display-area">
                <div className="value-container" style={{
                  color: korad?.output ? config.font_color : '#555',
                  textShadow: korad?.output ? `0 0 15px ${config.font_color}33` : 'none'
                }}>
                  {korad?.output ? (korad?.v_out || "00.00") : (korad?.v_set || "00.00")}
                </div>
                <div className="unit" style={{ color: korad?.output ? config.font_color : '#555' }}>V</div>
              </div>
              <div className="display-area">
                <div className="value-container" style={{
                  color: korad?.output ? config.font_color : '#555',
                  textShadow: korad?.output ? `0 0 15px ${config.font_color}33` : 'none'
                }}>
                  {korad?.output ? (korad?.i_out || "0.000") : (korad?.i_set || "0.000")}
                </div>
                <div className="unit" style={{ color: korad?.output ? config.font_color : '#555' }}>A</div>
              </div>
              <div className="psu-watts" style={{ color: config.watts_color, textShadow: `0 0 10px ${config.watts_color}80` }}>
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
