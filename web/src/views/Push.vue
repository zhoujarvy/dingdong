<template>
  <el-card style="max-width:760px">
    <el-form label-width="90px">
      <el-form-item label="接收终端">
        <el-select v-model="codes" multiple filterable placeholder="选择一个或多个终端"
                   style="width:100%">
          <el-option v-for="t in terminals" :key="t.code" :value="t.code"
                     :label="`${t.code} ${t.name}${t.online ? '（在线）' : '（离线）'}`"
                     :disabled="t.status !== 'active'" />
        </el-select>
      </el-form-item>
      <el-form-item label="发送方">
        <el-input v-model="form.sender" maxlength="50" />
      </el-form-item>
      <el-form-item label="消息标题">
        <el-input v-model="form.title" maxlength="200" placeholder="必填" />
      </el-form-item>
      <el-form-item label="消息内容">
        <el-input v-model="form.content" type="textarea" :rows="6" maxlength="20000"
                  placeholder="支持多行文本，终端点击弹窗后可在网页中查看全文" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="sending" @click="send">发 送</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card v-if="results" style="max-width:760px;margin-top:16px">
    <template #header>发送结果（送达 {{ results.delivered }}/{{ results.total }}）</template>
    <el-table :data="results.results" size="small">
      <el-table-column prop="terminal_code" label="终端编码" width="110" />
      <el-table-column prop="message_id" label="消息ID" width="90" />
      <el-table-column label="结果">
        <template #default="{ row }">
          <el-tag v-if="row.delivered" type="success" size="small">已实时送达</el-tag>
          <el-tag v-else-if="row.message_id" type="warning" size="small">已入库待补发</el-tag>
          <el-tag v-else type="danger" size="small">{{ row.error }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api'

const terminals = ref([])
const codes = ref([])
const form = ref({ sender: '管理后台', title: '', content: '' })
const sending = ref(false)
const results = ref(null)

async function loadTerminals() {
  const data = await http.get('/admin/terminals', { params: { page: 1, page_size: 500 } })
  terminals.value = data.items
}

async function send() {
  if (!codes.value.length) return ElMessage.warning('请选择接收终端')
  if (!form.value.title.trim()) return ElMessage.warning('请输入消息标题')
  sending.value = true
  try {
    results.value = await http.post('/admin/push', {
      terminal_codes: codes.value,
      title: form.value.title,
      content: form.value.content,
      sender: form.value.sender || '管理后台',
    })
    ElMessage.success('发送完成')
  } finally {
    sending.value = false
  }
}

onMounted(loadTerminals)
</script>
