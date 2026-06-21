<template>
  <main class="page">
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="page-card task-overview">
      <div class="overview-heading">
        <div>
          <h2>任务概览</h2>
          <p>当前任务的生成进度与异常分布</p>
        </div>
      </div>
      <div class="overview-metrics">
        <div class="overview-item">
          <span>全部任务</span>
          <strong>{{ summary.total }}</strong>
          <small>当前可见任务总数</small>
        </div>
        <div class="overview-item accent-blue">
          <span>处理中</span>
          <strong>{{ summary.active }}</strong>
          <small>待上传、校验或生成</small>
        </div>
        <div class="overview-item accent-green">
          <span>已完成</span>
          <strong>{{ summary.completed }}</strong>
          <small>可查看预览和下载</small>
        </div>
        <div class="overview-item accent-red">
          <span>异常任务</span>
          <strong>{{ summary.failed }}</strong>
          <small>失败或校验未通过</small>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="page-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="keyword"
            clearable
            placeholder="搜索任务名称、模板或主表"
            class="task-search"
          />
          <el-select v-model="selectedStatus" class="status-filter">
            <el-option
              v-for="option in taskStatusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </div>
        <div class="toolbar-right">
          <span class="result-count">筛选结果 {{ total }} 条</span>
          <el-button @click="loadTasks">刷新列表</el-button>
          <el-button type="primary" @click="createNewTask">新建任务</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tasks" border>
        <el-table-column label="任务" min-width="260">
          <template #default="{ row }">
            <div class="task-name">{{ row.task_name }}</div>
            <div class="task-id">{{ row.task_id }}</div>
          </template>
        </el-table-column>
        <el-table-column label="模板" min-width="220">
          <template #default="{ row }">
            <div>{{ row.template_name }}</div>
            <div class="muted small-text">主表：{{ row.main_table || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <StatusTag :status="row.status" :label="taskStatusText(row.status)" />
          </template>
        </el-table-column>
        <el-table-column label="产出" min-width="150">
          <template #default="{ row }">
            <div class="count-line">
              <strong>{{ row.success_count + row.failed_count }}</strong>
              <span>/ {{ row.total_rows || 0 }} 已处理</span>
            </div>
            <div class="muted small-text">成功 {{ row.success_count }}，失败 {{ row.failed_count }}</div>
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="190">
          <template #default="{ row }">
            <div>{{ formatTime(row.created_at) }}</div>
            <div class="muted small-text">更新：{{ formatTime(row.updated_at) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="主操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openResult(row.task_id)">{{ mainActionText(row.status) }}</el-button>
            <el-button
              v-if="['completed', 'partial_failed'].includes(row.status)"
              link
              type="primary"
              @click="downloadZip(row.task_id)"
            >
              下载 ZIP
            </el-button>
            <el-button link type="primary" @click="createFromTemplate(row.template_id)">新建同类</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="task-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="loadTasks"
          @size-change="handlePageSizeChange"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import StatusTag from '../components/common/StatusTag.vue'
import { downloadTaskZipUrl, listTasks } from '../api/tasks'
import type { TaskListItem, TaskStatus } from '../types/task'
import { isTaskActive, taskStatusOptions, taskStatusText } from '../utils/uiMeta'

const router = useRouter()
const tasks = ref<TaskListItem[]>([])
const loading = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const selectedStatus = ref<TaskStatus | 'all'>('all')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
let searchTimer: ReturnType<typeof setTimeout> | undefined

const summary = computed(() => {
  return {
    total: tasks.value.length,
    active: tasks.value.filter((task) => isTaskActive(task.status)).length,
    completed: tasks.value.filter((task) => task.status === 'completed').length,
    failed: tasks.value.filter((task) => ['failed', 'validation_failed', 'partial_failed'].includes(task.status)).length,
  }
})

onMounted(loadTasks)

watch([keyword, selectedStatus], () => {
  page.value = 1
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadTasks, 300)
})

async function loadTasks() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTasks({
      page: page.value,
      page_size: pageSize.value,
      status: selectedStatus.value === 'all' ? undefined : selectedStatus.value,
      keyword: keyword.value.trim() || undefined,
    })
    tasks.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务列表加载失败'
  } finally {
    loading.value = false
  }
}

function handlePageSizeChange() {
  page.value = 1
  loadTasks()
}

function createNewTask() {
  router.push('/tasks/create')
}

function openResult(taskId: string) {
  router.push(`/tasks/${taskId}/results`)
}

function createFromTemplate(templateId: number) {
  router.push({ path: '/tasks/new', query: { template_id: String(templateId) } })
}

function downloadZip(taskId: string) {
  window.open(downloadTaskZipUrl(taskId), '_blank')
}

function mainActionText(status: TaskStatus) {
  if (status === 'running') {
    return '查看进度'
  }
  if (status === 'completed' || status === 'partial_failed') {
    return '查看结果'
  }
  if (status === 'validation_failed') {
    return '查看校验'
  }
  if (status === 'validated') {
    return '查看生成入口'
  }
  return '查看任务'
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : '-'
}
</script>

<style scoped>
.task-search {
  width: 300px;
}

.status-filter {
  width: 160px;
}

.result-count,
.small-text {
  font-size: 12px;
}

.result-count {
  color: var(--color-text-muted);
}

.task-name {
  color: var(--color-text);
  font-weight: 700;
}

.task-id {
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 4px;
  overflow-wrap: anywhere;
}

.count-line {
  align-items: baseline;
  display: flex;
  gap: 4px;
}

.count-line strong {
  color: var(--color-primary);
  font-size: 18px;
}

.task-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.task-overview {
  display: grid;
  gap: 16px;
  padding: 18px;
}

.overview-heading {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.overview-heading h2 {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 750;
  margin: 0;
}

.overview-heading p {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 5px 0 0;
}

.overview-metrics {
  display: grid;
  gap: 1px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-border);
}

.overview-item {
  background: #fff;
  min-width: 0;
  padding: 16px 18px;
  position: relative;
}

.overview-item::before {
  background: #98a2b3;
  border-radius: 999px;
  content: "";
  height: 28px;
  left: 0;
  position: absolute;
  top: 18px;
  width: 3px;
}

.overview-item.accent-blue::before {
  background: #2458d3;
}

.overview-item.accent-green::before {
  background: #168456;
}

.overview-item.accent-red::before {
  background: #c0352b;
}

.overview-item span {
  color: var(--color-text-muted);
  display: block;
  font-size: 12px;
  font-weight: 700;
}

.overview-item strong {
  color: var(--color-text);
  display: block;
  font-size: 30px;
  line-height: 1;
  margin-top: 9px;
}

.overview-item small {
  color: var(--color-text-muted);
  display: block;
  font-size: 12px;
  margin-top: 8px;
}

@media (max-width: 1080px) {
  .overview-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
