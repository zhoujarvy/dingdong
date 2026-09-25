/** WebSocket 客户端：心跳 30s、断线退避重连 1s→60s、对齐 WPF WsClient 行为 */
import type { MessageData, Settings, WsStatus } from "./types";

const HEARTBEAT_MS = 30_000;
const RECONNECT_MIN = 1_000;
const RECONNECT_MAX = 60_000;

type Handlers = {
  onStatus: (s: WsStatus) => void;
  onUnread: (n: number) => void;
  onMessage: (m: MessageData) => void;
  onToken: (token: string) => void;
};

export class DdWs {
  private ws: WebSocket | null = null;
  private hbTimer: number | null = null;
  private reconnectTimer: number | null = null;
  private backoff = RECONNECT_MIN;
  private stopped = false;
  private notifiedIds = new Set<number>();

  constructor(
    private settings: () => Settings,
    private handlers: Handlers,
  ) {}

  start() {
    this.stopped = false;
    this.backoff = RECONNECT_MIN;
    this.connect();
  }

  stop() {
    this.stopped = true;
    this.cleanup();
    this.handlers.onStatus("offline");
  }

  private wsUrl(): string {
    const s = this.settings();
    const base = s.ServerUrl.replace(/\/+$/, "").replace(/^http/i, "ws");
    return `${base}/ws/${s.TerminalCode.toUpperCase()}`;
  }

  private connect() {
    if (this.stopped) return;
    this.cleanup();
    this.handlers.onStatus("connecting");
    let ws: WebSocket;
    try {
      ws = new WebSocket(this.wsUrl());
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;

    ws.onopen = () => {
      this.backoff = RECONNECT_MIN;
      this.handlers.onStatus("online");
      this.hbTimer = window.setInterval(() => this.send({ type: "heartbeat" }), HEARTBEAT_MS);
    };

    ws.onmessage = (ev) => {
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(ev.data as string);
      } catch {
        return;
      }
      switch (msg.type) {
        case "hello":
          this.handlers.onUnread(Number(msg.unread) || 0);
          if (typeof msg.inbox_token === "string" && msg.inbox_token) {
            this.handlers.onToken(msg.inbox_token);
          }
          break;
        case "message": {
          const data = msg.data as MessageData | undefined;
          if (data && !this.notifiedIds.has(data.id)) {
            this.notifiedIds.add(data.id);
            if (this.notifiedIds.size > 500) this.notifiedIds.clear();
            if (!data.read) this.handlers.onMessage(data);
          }
          break;
        }
        case "unread":
          this.handlers.onUnread(Number(msg.count) || 0);
          break;
        default:
          break; // heartbeat 应答等忽略
      }
    };

    ws.onclose = (ev) => {
      this.cleanup();
      // 4403 终端已注销 / 4404 终端不存在：停止重连
      if (ev.code === 4403) {
        this.stopped = true;
        this.handlers.onStatus("revoked");
        return;
      }
      if (ev.code === 4404) {
        this.stopped = true;
        this.handlers.onStatus("unknown");
        return;
      }
      this.handlers.onStatus("offline");
      this.scheduleReconnect();
    };

    ws.onerror = () => {
      /* onclose 会跟进处理 */
    };
  }

  private scheduleReconnect() {
    if (this.stopped || this.reconnectTimer !== null) return;
    const delay = this.backoff;
    this.backoff = Math.min(this.backoff * 2, RECONNECT_MAX);
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private send(payload: unknown) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  private cleanup() {
    if (this.hbTimer !== null) {
      clearInterval(this.hbTimer);
      this.hbTimer = null;
    }
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
  }
}
