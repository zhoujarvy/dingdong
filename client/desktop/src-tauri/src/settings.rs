//! 设置持久化：JSON 文件，字段与 WPF 客户端 Settings 一一对应。
//! 路径：{app_config_dir}/DingDong/settings.json

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase", default)]
pub struct Settings {
    pub server_url: String,
    pub terminal_code: String,
    pub terminal_name: String,
    pub inbox_token: String,
    pub sound_enabled: bool,
    pub tts_enabled: bool,
    /// "title" 仅标题 / "both" 标题+内容摘要
    pub tts_mode: String,
    pub auto_start: bool,
    /// 弹窗自动关闭秒数；0 = 不自动关闭（人工点击后关闭）。默认 60。
    pub notify_auto_close_sec: i64,
    /// 已退出登录（本地保留编码，可凭编码重新登录）
    pub logged_out: bool,
}

impl Default for Settings {
    /// 默认值与前端 defaultSettings() 一致：提示音开、TTS 关、朗读仅标题。
    fn default() -> Self {
        Self {
            server_url: String::new(),
            terminal_code: String::new(),
            terminal_name: String::new(),
            inbox_token: String::new(),
            sound_enabled: true,
            tts_enabled: false,
            tts_mode: "title".to_string(),
            auto_start: false,
            notify_auto_close_sec: 60,
            logged_out: false,
        }
    }
}

fn settings_path(app: &AppHandle) -> PathBuf {
    let dir = app
        .path()
        .app_config_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join("DingDong");
    let _ = fs::create_dir_all(&dir);
    dir.join("settings.json")
}

pub fn load(app: &AppHandle) -> Settings {
    let path = settings_path(app);
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

pub fn save(app: &AppHandle, s: &Settings) -> Result<(), String> {
    let path = settings_path(app);
    let json = serde_json::to_string_pretty(s).map_err(|e| e.to_string())?;
    fs::write(path, json).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn load_settings(app: AppHandle) -> Settings {
    load(&app)
}

#[tauri::command]
pub fn save_settings(app: AppHandle, settings: Settings) -> Result<(), String> {
    save(&app, &settings)
}

/// 调试日志：追加到 {app_config_dir}/DingDong/debug.log（排查弹窗/打开浏览器问题用）。
#[tauri::command]
pub fn debug_log(app: AppHandle, msg: String) {
    use std::io::Write;
    let dir = app
        .path()
        .app_config_dir()
        .unwrap_or_default()
        .join("DingDong");
    let _ = std::fs::create_dir_all(&dir);
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("debug.log"))
    {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        let _ = writeln!(f, "[{ts}] {msg}");
    }
}
