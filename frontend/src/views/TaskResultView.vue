<template>
  <main class="page">
    <div class="page-header">
      <div>
        <div class="page-kicker">Generated Assets</div>
        <h2 class="page-title">任务结果</h2>
        <p class="page-desc">{{ taskId }}</p>
      </div>
      <div class="actions">
        <el-button @click="goBack">返回任务列表</el-button>
        <el-button type="primary" @click="loadOutputs">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="metric-grid">
      <div class="metric-card">
        <div class="metric-label">输出文档</div>
        <div class="metric-value">{{ summary.total }}</div>
        <div class="metric-note">当前任务生成文件</div>
      </div>
      <div class="metric-card accent-green">
        <div class="metric-label">生成成功</div>
        <div class="metric-value">{{ summary.success }}</div>
        <div class="metric-note">可预览溯源与下载</div>
      </div>
      <div class="metric-card accent-blue">
        <div class="metric-label">溯源点</div>
        <div class="metric-value">{{ summary.traceCount }}</div>
        <div class="metric-note">字段、循环、条件、AI</div>
      </div>
      <div class="metric-card accent-purple">
        <div class="metric-label">AI 段落</div>
        <div class="metric-value">{{ summary.aiBlockCount }}</div>
        <div class="metric-note">AI 生成内容数量</div>
      </div>
    </section>

    <section class="page-card">
      <OutputDocumentList :task-id="taskId" :documents="documents" :loading="loading" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import OutputDocumentList from '../components/OutputDocumentList.vue'
import { listTaskOutputs } from '../api/tasks'
import type { DocumentRecord } from '../types/task'

const route = useRoute()
const router = useRouter()
const taskId = computed(() => String(route.params.taskId || route.query.task_id || ''))
const documents = ref<DocumentRecord[]>([])
const loading = ref(false)
const errorMessage = ref('')

const summary = computed(() => {
  return {
    total: documents.value.length,
    success: documents.value.filter((document) => document.status === 'success').length,
    traceCount: documents.value.reduce((sum, document) => sum + (document.trace_count || 0), 0),
    aiBlockCount: documents.value.reduce((sum, document) => sum + (document.ai_block_count || 0), 0),
  }
})

onMounted(loadOutputs)

async function loadOutputs() {
  if (!taskId.value) {
    errorMessage.value = '缺少 taskId'
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTaskOutputs(taskId.value)
    documents.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '输出文档加载失败'
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/tasks')
}
</script>

<style scoped>
.accent-green {
  border-color: #bfe8d5;
}

.accent-blue {
  border-color: #cfe0ff;
}

.accent-purple {
  border-color: #decfff;
}
</style>
