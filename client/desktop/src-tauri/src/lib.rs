//! 叮咚跨平台客户端（Tauri 2）
//! Rust 侧职责：托盘/角标、TTS、设置持久化、消息弹窗窗口、开机自启、单实例。

mod notify;
mod settings;
mod tray;
mod tts;

use tauri::{Manager, WindowEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            None,
        ))
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // 二次启动：唤起已有实例主窗口
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
                let _ = win.set_focus();
            }
        }))
        .setup(|app| {
            tray::init(app.handle())?;
            // visible:false 防闪白，就绪后立即显示
            if let Some(win) = app.get_webview_window("main") {
                let _ = win.show();
            }
            Ok(())
        })
        .on_window_event(|window, event| match event {
            // 主窗口点关闭 = 隐藏到托盘
            WindowEvent::CloseRequested { api, .. } => {
                if window.label() == "main" {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![
            settings::load_settings,
            settings::save_settings,
            tts::tts_speak,
            tray::set_tray_badge,
            tray::set_tray_tooltip,
            notify::show_notify,
            notify::close_notify,
            notify::my_label,
        ])
        .run(tauri::generate_context!())
        .expect("error while running dingdong desktop");
}
