<template>
  <el-card>
    <div class="toolbar">
      <el-radio-group v-model="status" @change="load">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="active">有效</el-radio-button>
        <el-radio-button value="revoked">已注销</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="createVisible = true">+ 新建终端</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="code" label="终端编码" width="120">
        <template #default="{ row }">
          <el-tag effect="plain" style="font-weight:bold">{{ row.code }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="终端名称" min-width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.status === 'revoked'" type="danger">已注销</el-tag>
          <el-tag v-else-if="row.online" type="success">在线</el-tag>
          <el-tag v-else type="info">离线</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="170" />
      <el-table-column prop="last_seen_at" label="最近连接" width="170" />
      <el-table-column prop="revoke_reason" label="注销原因" min-width="150" show-overflow-tooltip />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'active'" link type="danger" @click="revoke(row)">注销</el-button>
          <el-button v-else link type="primary" @click="restore(row)">恢复</el-button>
          <el-button link type="primary" @click="viewMsgs(row)">消息</el-button>
          <el-button link type="primary" @click="openInbox(row)">消息中心</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="total, prev, pager, next" style="margin-top:12px;justify-content:flex-end"
                   @current-change="load" />
  </el-card>

  <el-dialog v-model="createVisible" title="新建终端" width="420px">
    <el-form>
      <el-form-item label="终端名称">
        <el-input v-model="newName" placeholder="如：前台办公电脑" maxlength="50" />
      </el-form-item>
    </el-form>
    <div v-if="createdCode" class="created-code">
      终端编码：<b>{{ createdCode }}</b>（请在客户端设置中填入该编码）
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
import { useRouter } from 'vue-router'
import http from '../api'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')
const loading = ref(false)
const createVisible = ref(false)
const newName = ref('')
const creating = ref(false)
const createdCode = ref('')

async function load() {
  loading.value = true
  try {
    const data = await http.get('/admin/terminals', {
      params: { status: status.value, page: page.value, page_size: pageSize },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!newName.value.trim()) return ElMessage.warning('请输入终端名称')
  creating.value = true
  try {
    const data = await http.post('/admin/terminals', { name: newName.value.trim() })
    createdCode.value = data.code
    newName.value = ''
    load()
  } finally {
    creating.value = false
  }
}

async function revoke(row) {
  await ElMessageBox.confirm(`确定注销终端「${row.name}（${row.code}）」？注销后该终端将无法接收消息`, '确认')
  await http.post(`/admin/terminals/${row.id}/revoke`)
  ElMessage.success('已注销')
  load()
}

async function restore(row) {
  await http.post(`/admin/terminals/${row.id}/restore`)
  ElMessage.success('已恢复')
  load()
}

function viewMsgs(row) {
  router.push({ path: '/messages', query: { terminal_id: row.id } })
}

function openInbox(row) {
  window.open(`/t/${row.code}?token=${row.inbox_token}`, '_blank')
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.created-code { margin-top: 8px; color: #67c23a; }
</style>
