<template>
  <div>
    <div class="page-toolbar output-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">输出文档</span>
        <span class="toolbar-desc">共 {{ documents.length }} 份</span>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" :disabled="!taskId || !documents.length" @click="downloadZip">批量下载 ZIP</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="documents" border>
      <el-table-column label="文档" min-width="300">
        <template #default="{ row }">
          <div class="doc-name">{{ row.output_filename }}</div>
          <div class="muted small-text">{{ row.doc_id }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="primary_key_value" label="主键值" min-width="160" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <StatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column prop="trace_count" label="溯源数" width="100" />
      <el-table-column prop="ai_block_count" label="AI段落" width="100" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :disabled="row.status !== 'success'" @click="openPreview(row.doc_id)">
            查看预览与溯源
          </el-button>
          <el-button link type="primary" :disabled="row.status !== 'success'" @click="downloadDoc(row.doc_id)">
            下载 Word
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

.doc-name {
  color: var(--color-text);
  font-weight: 700;
  overflow-wrap: anywhere;
}

.small-text {
  font-size: 12px;
  margin-top: 4px;
}
</style>
