<template>
  <el-card>
    <div class="toolbar">
      <span class="tip">推送接口调用方凭据：调用 <code>POST /api/messages</code> 时在请求头携带
        <code>X-API-Key</code></span>
      <el-button type="primary" @click="createVisible = true">+ 新建密钥</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column label="密钥" min-width="320">
        <template #default="{ row }">
          <code class="key">{{ row.key }}</code>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.revoked" type="danger">已吊销</el-tag>
          <el-tag v-else type="success">有效</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" v-if="!row.revoked" @click="copy(row.key)">复制</el-button>
          <el-button link type="danger" v-if="!row.revoked" @click="revoke(row)">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="createVisible" title="新建 API 密钥" width="440px">
    <el-form>
      <el-form-item label="调用方名称">
        <el-input v-model="newName" placeholder="如：ERP 系统" maxlength="50" />
      </el-form-item>
    </el-form>
    <div v-if="createdKey" class="created-key">
      密钥已创建：<code>{{ createdKey }}</code>
      <el-button link type="primary" @click="copy(createdKey)">复制</el-button>
      <p style="color:#e6a23c;font-size:12px">请立即复制保存</p>
    </div>
    <template #footer>
      <el-button @click="createVisible = false">关闭</el-button>
      <el-button type="primary" :loading="creating" @click="create">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api'

const items = ref([])
const loading = ref(false)
const createVisible = ref(false)
const newName = ref('')
const creating = ref(false)
const createdKey = ref('')

async function load() {
  loading.value = true
  try {
    const data = await http.get('/admin/apikeys')
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!newName.value.trim()) return ElMessage.warning('请输入调用方名称')
  creating.value = true
  try {
    const data = await http.post('/admin/apikeys', { name: newName.value.trim() })
    createdKey.value = data.key
    newName.value = ''
    load()
  } finally {
    creating.value = false
  }
}

async function revoke(row) {
  await ElMessageBox.confirm(`确定吊销「${row.name}」的密钥？吊销后调用方将无法推送消息`, '确认')
  await http.post(`/admin/apikeys/${row.id}/revoke`)
  ElMessage.success('已吊销')
  load()
}

function copy(text) {
  navigator.clipboard?.writeText(text).then(
    () => ElMessage.success('已复制'),
    () => ElMessage.warning('复制失败，请手动复制')
  )
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.tip { color: #909399; font-size: 13px; }
.key { font-size: 13px; }
.created-key { margin-top: 8px; word-break: break-all; }
</style>
