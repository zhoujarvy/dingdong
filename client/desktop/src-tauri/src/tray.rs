//! 系统托盘：铃铛图标、未读数字角标（预生成 1-99 badge 图标）、右键菜单。

use tauri::{
    image::Image,
    menu::{MenuBuilder, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager,
};

const TRAY_ID: &str = "dingdong-tray";

fn bell_icon(app: &AppHandle) -> Option<Image<'static>> {
    // 使用编译期嵌入的应用默认图标（铃铛），dev 与打包环境行为一致。
    // Image::new_rgba：拷贝像素为_owned 数据，摆脱对 app 的借用。
    let icon = app.default_window_icon()?;
    Some(Image::new_owned(
        icon.rgba().to_vec(),
        icon.width(),
        icon.height(),
    ))
}

fn badge_icon(app: &AppHandle, unread: i64) -> Option<Image<'static>> {
    let n = unread.clamp(1, 99);
    let path = app
        .path()
        .resource_dir()
        .ok()?
        .join(format!("icons/badges/{}.png", n));
    let bytes = std::fs::read(path).ok()?;
    Image::from_bytes(&bytes).ok()
}

pub fn init(app: &AppHandle) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "打开消息中心", true, None::<&str>)?;
    let show = MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
    let menu = MenuBuilder::new(app).items(&[&open, &show]).separator().item(&quit).build()?;

    let icon = bell_icon(app);
    let mut builder = TrayIconBuilder::with_id(TRAY_ID)
        .tooltip("叮咚")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => {
                let _ = app.emit("tray-open-inbox", ());
            }
            "show" => {
                if let Some(win) = app.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.unminimize();
                    let _ = win.set_focus();
                }
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                let _ = app.emit("tray-open-inbox", ());
            }
        });
    if let Some(img) = icon {
        builder = builder.icon(img);
    }
    builder.build(app)?;
    Ok(())
}

/// 前端调用：更新托盘角标（0=恢复纯铃铛；1-99 数字角标；>99 显示 99）。
#[tauri::command]
pub fn set_tray_badge(app: AppHandle, unread: i64) {
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        let img = if unread > 0 {
            badge_icon(&app, unread).or_else(|| bell_icon(&app))
        } else {
            bell_icon(&app)
        };
        if let Some(img) = img {
            let _ = tray.set_icon(Some(img));
        }
    }
}

/// 前端调用：更新托盘 tooltip（编码/名称/连接状态）。
#[tauri::command]
pub fn set_tray_tooltip(app: AppHandle, tooltip: String) {
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        let tip: String = tooltip.chars().take(120).collect();
        let _ = tray.set_tooltip(Some(&tip));
    }
}
