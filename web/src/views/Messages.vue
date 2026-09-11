<template>
  <el-card>
    <div class="toolbar">
      <div>
        <el-select v-model="terminalId" placeholder="全部终端" clearable filterable
                   style="width:220px;margin-right:8px" @change="page = 1; load()">
          <el-option v-for="t in terminals" :key="t.id" :value="t.id"
                     :label="`${t.code} ${t.name}`" />
        </el-select>
        <el-select v-model="readFilter" style="width:120px" @change="page = 1; load()">
          <el-option value="" label="全部状态" />
          <el-option value="unread" label="未读" />
          <el-option value="read" label="已读" />
        </el-select>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="终端" width="170">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.terminal_code }}</el-tag>
          {{ row.terminal_name }}
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
      <el-table-column prop="sender" label="发送方" width="110" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="165" />
      <el-table-column prop="pushed_at" label="送达时间" width="165">
        <template #default="{ row }">{{ row.pushed_at || '未送达' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="140">
        <template #default="{ row }">
          <el-tag v-if="row.deleted_at" type="info" size="small">已删除</el-tag>
          <el-tag v-else-if="row.read_at" type="success" size="small">已读</el-tag>
          <el-tag v-else type="warning" size="small">未读</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openMsg(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
                   layout="total, prev, pager, next" style="margin-top:12px;justify-content:flex-end"
                   @current-change="load" />
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api'

const route = useRoute()
const items = ref([])
const terminals = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const terminalId = ref(Number(route.query.terminal_id) || null)
const readFilter = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await http.get('/admin/messages', {
      params: {
        terminal_id: terminalId.value || 0,
        read: readFilter.value,
        page: page.value,
        page_size: pageSize,
      },
    })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openMsg(row) {
  window.open(`/m/${row.id}?token=${row.access_token}`, '_blank')
}

onMounted(async () => {
  load()
  const data = await http.get('/admin/terminals', { params: { page: 1, page_size: 500 } })
  terminals.value = data.items
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
</style>
