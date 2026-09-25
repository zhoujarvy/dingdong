/** 全局状态：设置（Rust JSON 持久化）+ 连接状态 + 未读数 */
import { reactive } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { defaultSettings, type Settings, type WsStatus } from "./types";

export const settings = reactive<Settings>(defaultSettings());
export const state = reactive({
  status: "offline" as WsStatus,
  unread: 0,
  loaded: false,
});

export async function loadSettings() {
  try {
    const s = await invoke<Settings>("load_settings");
    Object.assign(settings, defaultSettings(), s);
  } finally {
    state.loaded = true;
  }
}

export async function saveSettings() {
  await invoke("save_settings", { settings: { ...settings } });
}

export function trayTooltip(): string {
  const s = settings;
  const statusText: Record<WsStatus, string> = {
    online: "已连接",
    connecting: "连接中",
    offline: "已断开",
    revoked: "已注销",
    unknown: "不存在",
  };
  let tip = `叮咚 - ${s.TerminalCode}`;
  if (s.TerminalName) tip += ` ${s.TerminalName}`;
  tip += ` (${statusText[state.status]})`;
  return tip;
}
