<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { enable as enableAutostart, disable as disableAutostart, isEnabled as isAutostartEnabled } from "@tauri-apps/plugin-autostart";
import { settings, saveSettings, state, trayTooltip } from "../store";
import { unregisterTerminal } from "../api";
import { splitServerUrl } from "../types";

const emit = defineEmits<{
  logout: [];
  unregister: [];
  "open-inbox": [];
  reconnect: [];
}>();

const parts = splitServerUrl(settings.ServerUrl);
const conn = reactive({ host: parts.host, port: parts.port });
const tip = ref("");
const confirmUnregister = ref(false);

const statusMeta = computed(() => {
  switch (state.status) {
    case "online": return { cls: "online", text: "已连接" };
    case "connecting": return { cls: "connecting", text: "连接中…" };
    case "revoked": return { cls: "revoked", text: "终端已注销" };
    case "unknown": return { cls: "revoked", text: "终端不存在" };
    default: return { cls: "offline", text: "已断开，自动重连中" };
  }
});

async function copyCode() {
  try {
    await navigator.clipboard.writeText(settings.TerminalCode);
    tip.value = "已复制终端编码";
    setTimeout(() => (tip.value = ""), 1500);
  } catch {
    /* ignore */
  }
}

async function save() {
  let serverChanged = false;
  if (conn.host.trim()) {
    const newUrl = `http://${conn.host.trim()}${conn.port && conn.port !== "80" ? ":" + conn.port : ""}`;
    serverChanged = newUrl !== settings.ServerUrl;
    settings.ServerUrl = newUrl;
  }
  await saveSettings();
  await invoke("set_tray_tooltip", { tooltip: trayTooltip() });
  if (serverChanged) {
    emit("reconnect");
    tip.value = "设置已保存，正在重新连接…";
  } else {
    tip.value = "设置已保存";
  }
  setTimeout(() => (tip.value = ""), 2500);
}

async function toggleAutoStart(on: boolean) {
  try {
    if (on) await enableAutostart();
    else await disableAutostart();
    settings.AutoStart = on;
  } catch {
    /* ignore */
  }
}

async function doUnregister() {
  try {
    await unregisterTerminal(settings.ServerUrl, settings.TerminalCode, settings.InboxToken);
  } catch {
    /* 失败不阻断本地重置 */
  }
  confirmUnregister.value = false;
  emit("unregister");
}

onMounted(async () => {
  // 同步一次系统自启状态
  try {
    settings.AutoStart = await isAutostartEnabled();
  } catch {
    /* ignore */
  }
});
</script>

<template>
  <div class="home">
    <!-- 终端状态卡 -->
    <div class="card">
      <div class="head-row">
        <span class="pill" :class="statusMeta.cls">
          <span class="dot" />{{ statusMeta.text }}
        </span>
        <span v-if="state.unread > 0" class="unread">{{ state.unread }} 条未读</span>
      </div>
      <div class="code-row">
        <span class="code">{{ settings.TerminalCode }}</span>
        <span class="name">{{ settings.TerminalName }}</span>
        <button class="btn small ghost" @click="copyCode">复制编码</button>
      </div>
      <div class="actions">
        <button class="btn primary" @click="emit('open-inbox')">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></svg>
          消息中心
        </button>
        <button class="btn warn" @click="emit('logout')">退出登录</button>
        <button class="btn danger" @click="confirmUnregister = true">注销终端</button>
      </div>
      <p class="hint">消息的查看、已读与删除均在网页消息中心进行，弹窗点击也会打开消息中心。</p>
    </div>

    <!-- 设置卡 -->
    <div class="card">
      <h3>连接</h3>
      <span class="label">服务器地址与端口</span>
      <div class="row">
        <input v-model="conn.host" class="input" />
        <input v-model="conn.port" class="input port" />
      </div>

      <h3 class="mt-lg">提醒方式</h3>
      <label class="check"><input v-model="settings.SoundEnabled" type="checkbox" /> 播放提示音</label>
      <label class="check"><input v-model="settings.TtsEnabled" type="checkbox" /> 语音朗读消息简介（系统语音）</label>
      <div v-if="settings.TtsEnabled" class="tts-mode">
        朗读内容：
        <select v-model="settings.TtsMode" class="select">
          <option value="title">仅标题</option>
          <option value="both">标题 + 内容摘要</option>
        </select>
      </div>
      <div class="tts-mode" style="margin-left:0">
        弹窗自动关闭：
        <select v-model.number="settings.NotifyAutoCloseSec" class="select">
          <option :value="10">10 秒</option>
          <option :value="30">30 秒</option>
          <option :value="60">60 秒（默认）</option>
          <option :value="180">3 分钟</option>
          <option :value="0">不自动关闭，点击后关闭</option>
        </select>
      </div>

      <h3 class="mt-lg">其他</h3>
      <label class="check">
        <input :checked="settings.AutoStart" type="checkbox" @change="toggleAutoStart(($event.target as HTMLInputElement).checked)" />
        开机自动启动（最小化到托盘）
      </label>

      <button class="btn primary block mt-lg" @click="save">保存设置</button>
    </div>

    <p class="footer-tip">关闭窗口将最小化到系统托盘，退出请使用托盘右键菜单。</p>
    <p v-if="tip" class="save-tip">{{ tip }}</p>

    <!-- 注销确认 -->
    <div v-if="confirmUnregister" class="mask" @click.self="confirmUnregister = false">
      <div class="card dialog">
        <h3>注销终端</h3>
        <p>确定注销此终端？注销后编号作废、不再接收消息，且无法再登录，只能重新注册。</p>
        <div class="dialog-actions">
          <button class="btn" @click="confirmUnregister = false">取消</button>
          <button class="btn danger" @click="doUnregister">确认注销</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home { height: 100%; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.head-row { display: flex; justify-content: space-between; align-items: center; }
.unread { color: var(--brand); font-size: 12.5px; }
.code-row { display: flex; align-items: flex-end; gap: 10px; margin-top: 12px; }
.code { font-size: 26px; font-weight: 700; color: var(--brand); letter-spacing: 1px; }
.name { font-size: 15px; color: var(--text-2); padding-bottom: 2px; flex: 1; }
.btn.ghost { margin-left: auto; color: var(--text-2); }
.actions { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.hint { font-size: 11.5px; color: var(--text-3); margin-top: 10px; }
h3 { font-size: 14px; margin-bottom: 4px; }
.row { display: flex; gap: 8px; }
.port { width: 84px; flex: none; }
.mt-lg { margin-top: 18px; }
.check { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 13.5px; cursor: pointer; }
.check input { accent-color: var(--brand); }
.tts-mode { display: flex; align-items: center; gap: 8px; margin: 10px 0 0 24px; font-size: 13px; color: var(--text-2); }
.tts-mode .select { width: 170px; height: 34px; }
.footer-tip { font-size: 11.5px; color: var(--text-3); text-align: center; }
.save-tip { font-size: 12.5px; color: var(--ok); text-align: center; }
.mask { position: fixed; inset: 0; background: rgb(0 0 0 / 40%); display: flex; align-items: center; justify-content: center; }
.dialog { width: 320px; }
.dialog p { margin: 10px 0 16px; color: var(--text-2); line-height: 1.7; font-size: 13.5px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; }
</style>
