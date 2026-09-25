/** 与 Rust settings.rs 的 Settings 一一对应（PascalCase 序列化） */
export interface Settings {
  ServerUrl: string;
  TerminalCode: string;
  TerminalName: string;
  InboxToken: string;
  SoundEnabled: boolean;
  TtsEnabled: boolean;
  TtsMode: "title" | "both";
  AutoStart: boolean;
  LoggedOut: boolean;
}

export function defaultSettings(): Settings {
  return {
    ServerUrl: "",
    TerminalCode: "",
    TerminalName: "",
    InboxToken: "",
    SoundEnabled: true,
    TtsEnabled: false,
    TtsMode: "title",
    AutoStart: false,
    LoggedOut: false,
  };
}

export type WsStatus = "connecting" | "online" | "offline" | "revoked" | "unknown";

export interface MessageData {
  id: number;
  title: string;
  content: string;
  sender: string;
  url: string;
  created_at: string;
  read: boolean;
}

export function splitServerUrl(url: string): { host: string; port: string } {
  let s = (url || "").trim().replace(/\/+$/, "");
  s = s.replace(/^https?:\/\//i, "");
  const idx = s.lastIndexOf(":");
  if (idx >= 0) {
    const p = s.slice(idx + 1);
    if (/^\d+$/.test(p)) return { host: s.slice(0, idx), port: p };
  }
  return { host: s, port: "80" };
}

export function buildServerUrl(host: string, port: string): string {
  const p = /^\d+$/.test(port) && port !== "80" ? `:${port}` : "";
  return `http://${host}${p}`;
}

export function inboxUrl(s: Settings, messageId?: number): string {
  const base = s.ServerUrl.replace(/\/+$/, "");
  const u = `${base}/t/${encodeURIComponent(s.TerminalCode)}?token=${encodeURIComponent(s.InboxToken)}`;
  return messageId ? `${u}&m=${messageId}` : u;
}
