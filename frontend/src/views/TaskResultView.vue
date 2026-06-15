<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">任务结果</h2>
        <p class="page-desc">{{ taskId }}</p>
      </div>
      <div class="actions">
        <el-button @click="goBack">返回任务列表</el-button>
        <el-button type="primary" @click="loadOutputs">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

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

<style scoped></style>
