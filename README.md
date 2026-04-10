# ⚡ LabMonitor

LabMonitor is a high-performance, ultra-lightweight desktop dashboard built to monitor electronics lab hardware in real-time. Originally prototyped in Python/Flet, the project has been fully architected on **Rust + Tauri** and **React**, resulting in instant startup times, practically zero background overhead, and an incredibly responsive SCPI hardware polling loop.

![LabMonitor Dashboard](screenshot.png)

## ✨ Features

- **Robust Hardware Support**: Native serial-port integration for **Owon XDM Series Multimeters** (e.g., XDM1041) and **Korad Power Supplies** (e.g., KA3005P, KD3005P).
- **Stream-Friendly UI**: A dark, vibrant, and premium user interface modeled around clear 7-segment digital displays. Tailored perfectly for readability when capturing on OBS overlays.
- **Deep Customization**: Native color pickers allow you to theme every aspect of the dashboard—from the mode chips to the ambient card backdrops and dynamic Watts/VDC glows.
- **Micro-Overhead**: Utilizing Rust's thread management, the raw SCPI polling loop stays completely decoupled from the frontend rendering, grabbing device states seamlessly without spiking your CPU.
- **Hardware Ping Tools**: Built-in backend connection tests next to the port selectors help immediately diagnose COM port availability and hardware locking conflicts.

## 🚀 Getting Started

### Prerequisites
- [Node.js](https://nodejs.org/) & npm
- [Rust](https://www.rust-lang.org/tools/install)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Krhomv/LabMonitor.git
   cd LabMonitor
   ```

2. Install the frontend dependencies:
   ```bash
   npm install
   ```

3. Fire up the development environment (featuring hot-reload):
   ```bash
   npm run tauri dev
   ```

4. Compile a standalone native OS executable bundle:
   ```bash
   npm run tauri build
   ```
   *Your compiled installer and portable binaries will be pushed to the `src-tauri/target/release/bundles/` directory.*

## ⚙️ Configuration
Click the gear `⚙` icon in the top right to open the application settings. From here, you can map the background worker threads to your specific Windows COM ports (e.g., `COM3`, `COM4`) and instantly tweak the application's visual presence.

## 🛠️ Technology Stack
- **Frontend**: `React`, `TypeScript`, `Vite`, Native Vanilla CSS
- **Backend / OS Layer**: `Rust`, `Tauri v2`, `serialport`
