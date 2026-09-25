<script setup lang="ts">
import { reactive, ref } from "vue";
import { loginTerminal, registerTerminal } from "../api";
import { settings } from "../store";
import { buildServerUrl, splitServerUrl } from "../types";

const props = defineProps<{ loggedOutCode: boolean }>();
const emit = defineEmits<{ done: [] }>();

const mode = ref<"register" | "login">(props.loggedOutCode ? "login" : "register");
const form = reactive({
  host: "",
  port: "80",
  name: "",
  code: "",
});
const busy = ref(false);
const tip = ref("");

// 初始化：拆解已保存 ServerUrl；退出登录时预填编码与名称
const parts = splitServerUrl(settings.ServerUrl);
form.host = parts.host || "127.0.0.1";
form.port = parts.port || "80";
if (props.loggedOutCode) {
  form.code = settings.TerminalCode;
  form.name = settings.TerminalName;
}

function switchMode() {
  mode.value = mode.value === "register" ? "login" : "register";
  tip.value = "";
}

async function submit() {
  if (!form.host.trim()) {
    tip.value = "请输入服务器地址";
    return;
  }
  const server = buildServerUrl(form.host.trim(), form.port.trim());
  try {
    busy.value = true;
    tip.value = mode.value === "register" ? "正在注册…" : "正在登录…";
    const identity =
      mode.value === "register"
        ? await registerTerminal(server, form.name.trim())
        : await loginTerminal(server, form.code.trim().toUpperCase(), form.name.trim());
    settings.ServerUrl = server;
    settings.TerminalCode = identity.code;
    settings.TerminalName = identity.name;
    settings.InboxToken = identity.inbox_token;
    settings.LoggedOut = false;
    emit("done");
  } catch (e) {
    tip.value = `${mode.value === "register" ? "注册" : "登录"}失败：${(e as Error).message}`;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="brand">
      <svg viewBox="0 0 24 24" width="56" height="56" aria-hidden="true">
        <path fill="#2f6fed" d="M12 2a6 6 0 0 0-6 6v3.6c0 .6-.24 1.18-.66 1.6L4 15.5h16l-1.34-1.9a2.4 2.4 0 0 1-.66-1.6V8a6 6 0 0 0-6-6z" />
        <path fill="#2f6fed" d="M9.5 17a2.5 2.5 0 0 0 5 0z" />
      </svg>
      <h1>叮咚</h1>
      <p>消息推送客户端</p>
    </div>

    <div class="card form">
      <span class="label">服务器地址与端口</span>
      <div class="row">
        <input v-model="form.host" class="input" placeholder="192.168.1.10" @keyup.enter="submit" />
        <input v-model="form.port" class="input port" placeholder="8000" @keyup.enter="submit" />
      </div>

      <template v-if="mode === 'register'">
        <span class="label mt">终端名称</span>
        <input v-model="form.name" class="input" placeholder="如：前台收银机" maxlength="50" @keyup.enter="submit" />
      </template>
      <template v-else>
        <span class="label mt">终端编码（6 位）</span>
        <input v-model="form.code" class="input" placeholder="A2B3C4" maxlength="6" @keyup.enter="submit" />
        <span class="label mt">终端名称（需与注册时一致）</span>
        <input v-model="form.name" class="input" placeholder="注册时填写的名称" maxlength="50" @keyup.enter="submit" />
      </template>

      <button class="btn primary block mt-lg" :disabled="busy" @click="submit">
        {{ mode === "register" ? "注册终端" : "登录" }}
      </button>

      <div class="switch" @click="switchMode">
        {{ mode === "register" ? "已有终端编码？点此登录" : "没有编码？点此注册新终端" }}
      </div>
      <div class="tip" :class="{ error: tip.includes('失败') }">{{ tip || (mode === 'register' ? '注册后将获得一个 6 位终端编码，请妥善保存' : '输入终端编码与名称登录，编号与名称保持不变') }}</div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 20px; gap: 20px;
}
.brand { text-align: center; }
.brand h1 { font-size: 24px; margin-top: 8px; letter-spacing: 6px; }
.brand p { color: var(--text-3); font-size: 13px; margin-top: 2px; }
.form { width: 100%; max-width: 340px; }
.row { display: flex; gap: 8px; }
.port { width: 84px; flex: none; }
.mt { margin-top: 14px; }
.mt-lg { margin-top: 20px; }
.switch {
  text-align: center; color: var(--brand); font-size: 12.5px;
  cursor: pointer; margin-top: 14px;
}
.switch:hover { text-decoration: underline; }
</style>
