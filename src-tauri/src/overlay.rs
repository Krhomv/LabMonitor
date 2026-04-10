use crate::config::ConfigManager;
use crate::devices::DeviceState;
use serde::Serialize;
use std::sync::Arc;
use warp::Filter;

#[derive(Serialize)]
struct OverlayState {
    owon: crate::devices::OwonData,
    korad: crate::devices::KoradData,
    config: OverlayConfig,
}

#[derive(Serialize)]
struct OverlayConfig {
    font_color: String,
    accent_color: String,
    device_bg_color: String,
    watts_color: String,
}

pub fn spawn_overlay_server(
    state: Arc<DeviceState>,
    config_manager: Arc<ConfigManager>,
    port: u16,
) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .expect("Failed to build tokio runtime for overlay server");

        rt.block_on(async move {
            let state = state.clone();
            let config_manager = config_manager.clone();

            // Shared state filter
            let state_filter = {
                let state = state.clone();
                let config_manager = config_manager.clone();
                warp::any().map(move || (state.clone(), config_manager.clone()))
            };

            // GET /api/state
            let api_state = warp::path!("api" / "state")
                .and(warp::get())
                .and(state_filter.clone())
                .map(|(state, config_mgr): (Arc<DeviceState>, Arc<ConfigManager>)| {
                    let owon = state.owon.lock().unwrap().clone();
                    let korad = state.korad.lock().unwrap().clone();
                    let cfg = config_mgr.config.lock().unwrap().clone();
                    let payload = OverlayState {
                        owon,
                        korad,
                        config: OverlayConfig {
                            font_color: cfg.font_color,
                            accent_color: cfg.accent_color,
                            device_bg_color: cfg.device_bg_color,
                            watts_color: cfg.watts_color,
                        },
                    };
                    warp::reply::json(&payload)
                });

            // GET /overlay/owon
            let overlay_owon = warp::path!("overlay" / "owon")
                .and(warp::get())
                .map(|| {
                    warp::reply::html(include_str!("overlay_owon.html"))
                });

            // GET /overlay/korad
            let overlay_korad = warp::path!("overlay" / "korad")
                .and(warp::get())
                .map(|| {
                    warp::reply::html(include_str!("overlay_korad.html"))
                });

            let routes = api_state
                .or(overlay_owon)
                .or(overlay_korad);

            println!("[LabMonitor] OBS overlay server running on http://localhost:{}", port);

            warp::serve(routes)
                .run(([127, 0, 0, 1], port))
                .await;
        });
    });
}
