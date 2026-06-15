<template>
  <div>
    <div class="page-toolbar output-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">输出文档</span>
        <span class="toolbar-desc">共 {{ documents.length }} 份</span>
      </div>
      <div class="toolbar-right">
        <el-button :disabled="!taskId" @click="downloadZip">下载 ZIP</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="documents" border>
      <el-table-column prop="output_filename" label="文档" min-width="260" />
      <el-table-column prop="primary_key_value" label="主键值" min-width="160" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <StatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column prop="trace_count" label="溯源数" width="100" />
      <el-table-column prop="ai_block_count" label="AI段落" width="100" />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.status !== 'success'" @click="openPreview(row.doc_id)">
            预览溯源
          </el-button>
          <el-button link type="primary" :disabled="row.status !== 'success'" @click="downloadDoc(row.doc_id)">
            下载
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import StatusTag from './common/StatusTag.vue'
import { downloadDocumentUrl } from '../api/documents'
import { downloadTaskZipUrl } from '../api/tasks'
import type { DocumentRecord } from '../types/task'

const props = defineProps<{
  taskId: string
  documents: DocumentRecord[]
  loading?: boolean
}>()

const router = useRouter()

function openPreview(docId: string) {
  router.push(`/documents/${docId}`)
}

function downloadDoc(docId: string) {
  window.open(downloadDocumentUrl(docId), '_blank')
}

function downloadZip() {
  if (!props.taskId) {
    return
  }
  window.open(downloadTaskZipUrl(props.taskId), '_blank')
}
</script>

<style scoped>
.output-toolbar {
  margin-bottom: 16px;
}

.toolbar-title {
  color: #1f2937;
  font-weight: 650;
}

.toolbar-desc {
  color: #667085;
  font-size: 13px;
}
</style>
