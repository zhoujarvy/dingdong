//! 设置持久化：JSON 文件，字段与 WPF 客户端 Settings 一一对应。
//! 路径：{app_config_dir}/DingDong/settings.json

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
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
    /// 已退出登录（本地保留编码，可凭编码重新登录）
    pub logged_out: bool,
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
