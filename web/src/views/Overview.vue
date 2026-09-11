<template>
  <el-row :gutter="16">
    <el-col :span="6" v-for="card in cards" :key="card.label">
      <el-card class="stat-card">
        <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
        <div class="stat-label">{{ card.label }}</div>
      </el-card>
    </el-col>
  </el-row>
  <el-card style="margin-top:16px">
    <template #header>使用说明</template>
    <ol style="line-height:2;color:#606266;padding-left:20px;margin:0">
      <li>Windows 客户端首次运行时填写服务器地址并注册终端，获得 6 位终端编码</li>
      <li>在「API 密钥」页创建密钥，供第三方程序推送消息时携带</li>
      <li>第三方程序调用 <code>POST /api/messages</code>，请求头带 <code>X-API-Key</code>，消息即时送达在线终端</li>
      <li>终端超过 {{ offlineDays }} 天未连接服务器将被自动注销</li>
    </ol>
  </el-card>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import http from '../api'

const data = ref({})
const offlineDays = 30

onMounted(async () => {
  data.value = await http.get('/admin/overview')
})

const cards = computed(() => [
  { label: '在线终端', value: data.value.terminals_online ?? '-', color: '#67c23a' },
  { label: '有效终端', value: data.value.terminals_active ?? '-', color: '#409eff' },
  { label: '今日消息', value: data.value.messages_today ?? '-', color: '#e6a23c' },
  { label: '待补发消息', value: data.value.messages_pending ?? '-', color: '#f56c6c' },
])
</script>

<style scoped>
.stat-card { text-align: center; }
.stat-value { font-size: 34px; font-weight: 700; }
.stat-label { color: #909399; margin-top: 4px; }
</style>
