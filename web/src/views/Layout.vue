<template>
  <el-container style="height:100%">
    <el-aside width="200px" class="aside">
      <div class="logo">🔔 叮咚</div>
      <el-menu :default-active="$route.path" router background-color="#001529"
               text-color="#a6adb4" active-text-color="#ffffff">
        <el-menu-item index="/overview">📊 总览</el-menu-item>
        <el-menu-item index="/terminals">💻 终端管理</el-menu-item>
        <el-menu-item index="/messages">📨 消息记录</el-menu-item>
        <el-menu-item index="/apikeys">🔑 API 密钥</el-menu-item>
        <el-menu-item index="/push">📤 发送消息</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="crumb">{{ $route.meta.title }}</span>
        <el-button link @click="logout">退出登录</el-button>
      </el-header>
      <el-main style="background:#f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { clearToken } from '../auth'

const router = useRouter()
function logout() {
  clearToken()
  router.push('/login')
}
</script>

<style scoped>
.aside { background: #001529; }
.logo {
  color: #fff; font-size: 20px; font-weight: 700; letter-spacing: 2px;
  text-align: center; padding: 20px 0;
}
.el-menu { border-right: none; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid #ebeef5;
}
.crumb { font-size: 15px; font-weight: 600; }
</style>
