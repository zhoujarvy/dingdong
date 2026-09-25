<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { openUrl } from "@tauri-apps/plugin-opener";
import AppLogin from "./views/Login.vue";
import AppHome from "./views/Home.vue";
import { DdWs } from "./ws";
import { loadSettings, saveSettings, settings, state, trayTooltip } from "./store";
import { playDing } from "./sound";
import { inboxUrl, type MessageData } from "./types";

const view = ref<"loading" | "login" | "home">("loading");
let ws: DdWs | null = null;
let unlisteners: UnlistenFn[] = [];

const loggedOutWithCode = computed(
  () => settings.LoggedOut && settings.TerminalCode.length === 6,
);

async function persist() {
  await saveSettings();
  await invoke("set_tray_tooltip", { tooltip: trayTooltip() });
}

function updateBadge() {
  invoke("set_tray_badge", { unread: state.unread }).catch(() => {});
  invoke("set_tray_tooltip", { tooltip: trayTooltip() }).catch(() => {});
}

function startWs() {
  stopWs();
  ws = new DdWs(
    () => ({ ...settings }),
    {
      onStatus(s) {
        state.status = s;
        updateBadge();
        if (s === "revoked" || s === "unknown") {
          // 终端被注销/不存在：清空身份回登录页（对齐 WPF 行为）
          settings.TerminalCode = "";
          settings.TerminalName = "";
          settings.InboxToken = "";
          settings.LoggedOut = false;
          persist().catch(() => {});
          stopWs();
          view.value = "login";
        }
      },
      onUnread(n) {
        state.unread = n;
        updateBadge();
      },
      onToken(token) {
        if (token && token !== settings.InboxToken) {
          settings.InboxToken = token;
          persist().catch(() => {});
        }
      },
      onMessage(m: MessageData) {
        state.unread++;
        updateBadge();
        if (settings.SoundEnabled) playDing();
        if (settings.TtsEnabled) {
          const brief =
            settings.TtsMode === "both" && m.content
              ? `${m.title}。${m.content.slice(0, 60)}`
              : m.title;
          invoke("tts_speak", { text: brief }).catch(() => {});
        }
        invoke("show_notify", {
          messageId: m.id,
          title: m.title,
          content: m.content,
          sender: m.sender,
          url: m.url?.startsWith("http") ? m.url : settings.ServerUrl.replace(/\/+$/, "") + (m.url || ""),
          closeSec: settings.NotifyAutoCloseSec,
        }).catch((e) => {
          alert(`弹窗创建失败：${(e as Error).message || String(e)}`);
        });
      },
    },
  );
  ws.start();
}

function stopWs() {
  ws?.stop();
  ws = null;
}

function enterHome() {
  view.value = "home";
  state.unread = 0;
  // 注册/登录成功即落盘身份（否则重启丢失登录态，只有 hello 令牌变化才会保存）
  persist().catch(() => {});
  updateBadge();
  startWs();
}

function backToLogin(keepCode: boolean) {
  stopWs();
  settings.LoggedOut = keepCode;
  if (!keepCode) {
    settings.TerminalCode = "";
    settings.TerminalName = "";
    settings.InboxToken = "";
  }
  state.unread = 0;
  persist().catch(() => {});
  updateBadge();
  view.value = "login";
}

async function openInbox(messageId?: number) {
  const log = (m: string) => invoke("debug_log", { msg: m }).catch(() => {});
  log(`openInbox code=${settings.TerminalCode} token=${settings.InboxToken ? "yes" : "NO"}`);
  if (!settings.TerminalCode || !settings.InboxToken) {
    alert("尚未登录或令牌未同步，暂时无法打开消息中心。");
    return;
  }
  const target = inboxUrl(settings, messageId);
  try {
    await openUrl(target);
    log(`openUrl ok: ${target}`);
  } catch (e) {
    log(`openUrl FAILED: ${target} err=${(e as Error).message || String(e)}`);
    alert(`打开消息中心失败：${(e as Error).message}`);
  }
}

onMounted(async () => {
  await loadSettings();
  // 托盘事件：左键单击 / 菜单「打开消息中心」
  unlisteners.push(
    await listen("tray-open-inbox", () => openInbox()),
  );
  if (!(settings.ServerUrl && settings.TerminalCode)) {
    view.value = "login";
  } else if (!settings.LoggedOut) {
    view.value = "home";
    startWs();
  } else {
    view.value = "login";
  }
});

onUnmounted(() => {
  stopWs();
  unlisteners.forEach((u) => u());
  unlisteners = [];
});

// 供 Home 组件复用
defineExpose({ openInbox });
</script>

<template>
  <div class="app-root">
    <div v-if="view === 'loading'" class="loading">
      <div class="bell">🔔</div>
    </div>
    <AppLogin v-else-if="view === 'login'" :logged-out-code="loggedOutWithCode" @done="enterHome" />
    <AppHome
      v-else
      @logout="backToLogin(true)"
      @unregister="backToLogin(false)"
      @open-inbox="openInbox()"
      @reconnect="startWs"
    />
  </div>
</template>

<style scoped>
.app-root { height: 100%; }
.loading { height: 100%; display: flex; align-items: center; justify-content: center; }
.bell { font-size: 44px; }
</style>
