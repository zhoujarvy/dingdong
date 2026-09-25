//! 右下角消息弹窗：无边框小窗，多层堆叠，5 秒自动关闭由前端控制。

use std::sync::atomic::{AtomicI64, Ordering};
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

static NOTIFY_SEQ: AtomicI64 = AtomicI64::new(0);
const NOTIFY_W: f64 = 360.0;
const NOTIFY_H: f64 = 96.0;
const NOTIFY_GAP: f64 = 8.0;

/// 弹窗堆叠基准：屏幕右下角向上排列，超过 4 个后回到最底部。
fn notify_slots(app: &AppHandle) -> Vec<(f64, f64)> {
    let mut slots = Vec::new();
    if let Some(monitor) = app.primary_monitor().ok().flatten() {
        let size = monitor.size();
        let scale = monitor.scale_factor();
        let screen_h = size.height as f64 / scale;
        let screen_w = size.width as f64 / scale;
        let base_y = screen_h - NOTIFY_H - 12.0;
        let base_x = screen_w - NOTIFY_W - 12.0;
        for i in 0..4i64 {
            slots.push((base_x, base_y - i as f64 * (NOTIFY_H + NOTIFY_GAP)));
        }
    }
    if slots.is_empty() {
        slots.push((200.0, 200.0));
    }
    slots
}

pub fn active_count(app: &AppHandle) -> usize {
    app.webview_windows()
        .keys()
        .filter(|l| l.starts_with("notify-"))
        .count()
}

/// 前端调用：弹出消息提醒小窗。
#[tauri::command]
pub fn show_notify(app: AppHandle, message_id: i64, title: String, content: String, sender: String, url: String) -> Result<(), String> {
    let idx = (active_count(&app) % 4) as i64;
    let (x, y) = notify_slots(&app)[idx as usize];
    let seq = NOTIFY_SEQ.fetch_add(1, Ordering::SeqCst);
    let label = format!("notify-{}", seq);

    let query = format!(
        "?id={}&title={}&content={}&sender={}&url={}",
        message_id,
        urlencoding_encode(&title),
        urlencoding_encode(&content),
        urlencoding_encode(&sender),
        urlencoding_encode(&url),
    );
    let url = WebviewUrl::App(format!("notify.html{}", query).into());

    let win = WebviewWindowBuilder::new(&app, &label, url)
        .title("叮咚消息")
        .inner_size(NOTIFY_W, NOTIFY_H)
        .position(x, y)
        .decorations(false)
        .always_on_top(true)
        .skip_taskbar(true)
        .resizable(false)
        .shadow(false)
        .focused(false)
        .build()
        .map_err(|e| e.to_string())?;
    let _ = win.set_focus();
    Ok(())
}

/// 前端调用：关闭指定弹窗。
#[tauri::command]
pub fn close_notify(app: AppHandle, label: String) {
    if label.starts_with("notify-") {
        if let Some(win) = app.get_webview_window(&label) {
            let _ = win.close();
        }
    }
}

/// 弹窗窗口自身查询自己的 label（用于关闭）。
#[tauri::command]
pub fn my_label(window: tauri::WebviewWindow) -> String {
    window.label().to_string()
}

fn urlencoding_encode(s: &str) -> String {
    // 仅编码弹窗 URL query 中不安全的字符，避免引号/换破坏 query 结构
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        match b {
            b'0'..=b'9' | b'A'..=b'Z' | b'a'..=b'z' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{:02X}", b)),
        }
    }
    out
}
