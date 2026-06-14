<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2>任务管理</h2>
        <p>创建任务、查看生成状态和输出结果。</p>
      </div>
      <div class="actions">
        <el-button @click="loadTasks">刷新</el-button>
        <el-button type="primary" @click="createNewTask">新建任务</el-button>
      </div>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <el-table v-loading="loading" :data="tasks" border>
      <el-table-column prop="task_name" label="任务名称" min-width="220" />
      <el-table-column prop="template_name" label="模板" min-width="220" />
      <el-table-column label="状态" width="140">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total_rows" label="总数" width="90" />
      <el-table-column prop="success_count" label="成功" width="90" />
      <el-table-column prop="failed_count" label="失败" width="90" />
      <el-table-column prop="error_count" label="错误" width="90" />
      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button link type="primary" @click="openResult(row.task_id)">查看结果</el-button>
        </template>
      </el-table-column>
    </el-table>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { listTasks } from '../api/tasks'
import type { TaskListItem, TaskStatus } from '../types/task'

const router = useRouter()
const tasks = ref<TaskListItem[]>([])
const loading = ref(false)
const errorMessage = ref('')

onMounted(loadTasks)

async function loadTasks() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTasks()
    tasks.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务列表加载失败'
  } finally {
    loading.value = false
  }
}

function createNewTask() {
  router.push('/tasks/create')
}

function openResult(taskId: string) {
  router.push(`/tasks/${taskId}/results`)
}

function statusType(status: TaskStatus) {
  if (status === 'completed' || status === 'validated') {
    return 'success'
  }
  if (status === 'failed' || status === 'validation_failed') {
    return 'danger'
  }
  if (status === 'running' || status === 'validating') {
    return 'warning'
  }
  return 'info'
}

function statusText(status: TaskStatus) {
  const map: Record<TaskStatus, string> = {
    created: '已创建',
    uploaded: '已上传',
    validating: '校验中',
    validated: '已校验',
    validation_failed: '校验失败',
    running: '生成中',
    completed: '已完成',
    partial_failed: '部分失败',
    failed: '失败',
    deleted: '已删除',
  }
  return map[status] || status
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : '-'
}
</script>

<style scoped>
.page {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.page-header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2 {
  margin: 0 0 6px;
}

.page-header p {
  color: #606266;
  margin: 0;
}

.actions {
  display: flex;
  gap: 8px;
}
</style>
