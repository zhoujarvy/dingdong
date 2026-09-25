//! TTS 语音朗读：调用各平台系统命令，spawn 不阻塞。
//! - Windows: powershell + System.Speech（SAPI）
//! - macOS: say
//! - Linux: spd-say（缺失时回退 espeak-ng）

use std::process::Command;

fn escape_ps(text: &str) -> String {
    text.replace('\'', "''")
}

pub fn speak_async(text: &str) {
    if text.trim().is_empty() {
        return;
    }
    let text = text.to_string();
    std::thread::spawn(move || {
        let _ = speak(&text);
    });
}

fn speak(text: &str) -> std::io::Result<()> {
    if cfg!(windows) {
        Command::new("powershell")
            .args([
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                &format!(
                    "Add-Type -AssemblyName System.Speech; \
                     $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; \
                     $s.Speak('{}')",
                     escape_ps(text)
                ),
            ])
            .spawn()?;
    } else if cfg!(target_os = "macos") {
        Command::new("say").arg(text).spawn()?;
    } else {
        // Linux：优先 spd-say，缺失回退 espeak-ng
        let ok = Command::new("sh")
            .arg("-c")
            .arg(format!(
                "command -v spd-say >/dev/null 2>&1 && printf '%s' \"$1\" | spd-say || espeak-ng \"$1\"",
            ))
            .arg("--")
            .arg(text)
            .spawn();
        if ok.is_err() {
            return Ok(());
        }
    }
    Ok(())
}

/// 前端调用：朗读消息简介（title 或 title+内容前 60 字）。
#[tauri::command]
pub fn tts_speak(text: String) {
    speak_async(&text);
}
