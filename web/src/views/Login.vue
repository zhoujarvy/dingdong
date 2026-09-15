<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="brand">
        <span class="logo">🔔</span>
        <h2>叮咚</h2>
        <p>消息推送管理后台</p>
      </div>
      <el-form @keyup.enter="submit">
        <el-form-item>
          <el-input v-model="password" type="password" placeholder="管理密码"
                    size="large" show-password autofocus />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading"
                   @click="submit">登 录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api'
import { setRole, setToken } from '../auth'

const router = useRouter()
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!password.value) return
  loading.value = true
  try {
    const data = await http.post('/admin/login', { password: password.value })
    setToken(data.token)
    setRole(data.role || 'admin')
    router.push(data.role === 'oper' ? '/push' : '/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f6feb 0%, #409eff 50%, #79bbff 100%);
}
.login-card { width: 360px; border-radius: 12px; }
.brand { text-align: center; margin-bottom: 24px; }
.logo { font-size: 42px; }
.brand h2 { margin: 8px 0 4px; letter-spacing: 4px; }
.brand p { color: #909399; font-size: 13px; margin: 0; }
</style>
