# LabMonitor - Project Summary

## Initial Plan
The goal was to create a professional, high-visibility Windows application for electronics livestreams to monitor two specific bench instruments:
1.  **Owon XDM1041 Multimeter:** Connect via serial (SCPI) to show live measurements and active modes (Volt, Amp, Ohm, etc.).
2.  **Korad KA3005PS PSU:** Connect via serial (ASCII) to show live Voltage, Amperage, Wattage, and status (Output ON/OFF, OVP/OCP).

### Key Requirements:
*   **Visuals:** Large, high-contrast fonts optimized for camera/livestream readability.
*   **Layout:** Stacked UI with Multimeter on top and PSU on the bottom.
*   **Settings:** Persistent configuration for COM ports and theme colors (Background/Font).
*   **Portability:** Easy to transfer to other machines as a single executable.
*   **Reliability:** Auto-reconnect on startup and a "Simulated" mode for testing without hardware.

---

## Tech Stack
*   **Language:** Python 3.12
*   **UI Framework:** [Flet](https://flet.dev/) (Flutter-based) for professional, hardware-accelerated visuals.
*   **Serial Communication:** `pyserial` for robust instrument control.
*   **Packaging:** `flet build windows` for standalone distribution.

---

## Accomplishments (So Far)

### 1. Hardware Integration Layer
*   Implemented `DeviceBase` for shared serial logic.
*   **Owon Class:** Handles SCPI commands (`:MEAS?`, `:FUNC?`, `*IDN?`) at 115200 baud.
*   **Korad Class:** Handles ASCII protocol (`VOUT1?`, `IOUT1?`, `STATUS?`) at 9600 baud.
*   **Simulation Mode:** Built-in data generators for both devices to allow UI testing.

### 2. Core UI Implementation
*   **Multimeter Section:** Features a dynamic "Mode Bar" that highlights the active measurement type and a massive digital-style value readout.
*   **PSU Section:** Displays live V/A/W, target setpoints, and a large, color-coded "OUTPUT ON/OFF" status badge.
*   **Multi-threading:** Polling logic runs on a background thread to keep the UI responsive at all times.

### 3. Settings & Persistence
*   **Config Manager:** Loads and saves settings to `config.json`.
*   **Settings Menu:** Allows selection of COM ports from a detected list, background color customization, and font color customization.

### 4. Environment-Specific Fixes
We successfully navigated several Flet 0.84.0 version-specific challenges:
*   **Attribute Corrections:** Updated all UI constants to the required TitleCase/Uppercase format (e.g., `ft.Colors`, `ft.Alignment.CENTER`, `ft.Icons`).
*   **Rendering Backend:** Bypassed the standard Flet routing system (`page.go`) in favor of **Conditional Content Swapping**, which resolved "Black Screen" and "Empty View List" errors on your system.
*   **Compatibility:** Removed unsupported features like `letter_spacing` to ensure a clean launch.

---

## Current Status
The application is **functional and stable**. It launches directly into the monitor view, displays simulated data by default, and allows you to configure your hardware ports through the gear icon in the top right.

## Next Steps for Resume
1.  **Hardware Validation:** Connect the physical Owon and Korad units and test the real-world serial response.
2.  **Fine-Tuning:** Adjust font sizes or colors based on how it looks through your streaming software (OBS/vMix).
3.  **Executable Build:** Run `flet build windows` to generate the final portable application.
