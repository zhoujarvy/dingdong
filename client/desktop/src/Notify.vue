<script setup lang="ts">
import { onMounted, ref } from "vue";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";

const params = new URLSearchParams(window.location.search);
const title = ref(params.get("title") || "新消息");
const content = ref(params.get("content") || "");
const sender = ref(params.get("sender") || "");
const url = ref(params.get("url") || "");
const closeSec = Number(params.get("close")) || 0;
const label = ref("");
const closing = ref(false);

function decode(s: string): string {
  // URL 编码的内容按 UTF-8 解码（Rust 侧按字节百分号编码）
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}
title.value = decode(title.value);
content.value = decode(content.value);
sender.value = decode(sender.value);
url.value = decode(url.value);

async function close() {
  if (closing.value) return;
  closing.value = true;
  if (label.value.startsWith("notify-")) {
    await invoke("close_notify", { label: label.value }).catch(() => {});
  } else {
    window.close();
  }
}

async function openMessage() {
  if (url.value) {
    try {
      await openUrl(url.value);
    } catch {
      /* ignore */
    }
  }
  close();
}

onMounted(async () => {
  try {
    label.value = await invoke<string>("my_label");
  } catch {
    /* 非 Tauri 环境（vite dev 直开） */
  }
  // close>0：到期自动关闭；0 = 不自动关闭，等待人工点击
  if (closeSec > 0) setTimeout(close, closeSec * 1000);
});
</script>

<template>
  <div class="notify" @click="openMessage">
    <div class="bell">
      <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    </div>
    <div class="body">
      <div class="title">{{ title }}</div>
      <div v-if="content" class="content">{{ content.slice(0, 80) }}</div>
      <div class="meta">叮咚{{ sender ? " · " + sender : "" }} · {{ closeSec > 0 ? "点击查看" : "点击查看并关闭" }}</div>
    </div>
  </div>
</template>

<style scoped>
.notify {
  height: 100vh; display: flex; gap: 12px; padding: 14px; cursor: pointer;
  background: #ffffff; color: #26303b; border-radius: 12px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 18%);
  border: 1px solid #e4e7ed; overflow: hidden;
  transition: transform .12s;
}
.notify:hover { transform: translateY(-1px); }
.notify:active { transform: scale(.99); }
.bell {
  flex: none; width: 40px; height: 40px; border-radius: 50%;
  background: #2f6fed; display: flex; align-items: center; justify-content: center;
}
.body { min-width: 0; flex: 1; }
.title {
  font-size: 14px; font-weight: 600; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.content {
  font-size: 12.5px; color: #606266; margin-top: 4px; line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.meta { font-size: 11px; color: #909399; margin-top: 6px; }
</style>
