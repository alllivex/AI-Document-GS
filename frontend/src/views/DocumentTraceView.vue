<template>
  <main class="trace-page">
    <DocumentNavBar
      :doc-id="docId"
      :title="preview?.title"
      :output-file="preview?.output_file"
      @back="goBack"
      @download="downloadCurrentDocument"
    />

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="trace-layout">
      <div v-loading="loadingPreview" class="preview-pane">
        <PreviewRenderer
          :preview="preview"
          :selected-trace-id="selectedTraceId"
          @select-trace="selectTrace"
        />
      </div>
      <TraceDetailPanel :trace-item="selectedTraceItem" :loading="loadingTrace" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DocumentNavBar from '../components/DocumentNavBar.vue'
import PreviewRenderer from '../components/PreviewRenderer.vue'
import TraceDetailPanel from '../components/TraceDetailPanel.vue'
import { downloadDocumentUrl, getDocumentPreview } from '../api/documents'
import { getTraceItem } from '../api/trace'

interface PreviewFile {
  doc_id?: string
  task_id?: string
  title?: string
  output_file?: string
  blocks?: PreviewBlock[]
}

interface PreviewRun {
  text: string
  trace_id: string | null
  ai_block_id?: string | null
  style?: {
    bold?: boolean | null
    italic?: boolean | null
    underline?: boolean | null
  } | null
}

interface PreviewTableCell {
  text: string
  trace_id: string | null
  ai_block_id?: string | null
}

type PreviewBlock =
  | {
      type: 'heading'
      block_id: string
      level: 1 | 2 | 3 | 4 | 5 | 6
      text: string
    }
  | {
      type: 'paragraph'
      block_id: string
      runs: PreviewRun[]
    }
  | {
      type: 'table'
      block_id: string
      headers: PreviewTableCell[]
      rows: PreviewTableCell[][]
    }

interface TraceItem {
  trace_id: string
  table_name?: string
  table_name_cn?: string
  field_name?: string
  field_name_cn?: string
  source_file?: string
  excel_row_number?: number
  excel_column_letter?: string | null
  raw_value?: unknown
  display_value?: string
}

const route = useRoute()
const router = useRouter()
const docId = computed(() => String(route.params.docId || ''))
const preview = ref<PreviewFile | null>(null)
const selectedTraceId = ref<string | null>(null)
const selectedTraceItem = ref<TraceItem | null>(null)
const loadingPreview = ref(false)
const loadingTrace = ref(false)
const errorMessage = ref('')

onMounted(loadPreview)

async function loadPreview() {
  if (!docId.value) {
    errorMessage.value = '缺少文档 ID'
    return
  }

  loadingPreview.value = true
  errorMessage.value = ''
  try {
    preview.value = await getDocumentPreview(docId.value) as PreviewFile
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '预览加载失败'
  } finally {
    loadingPreview.value = false
  }
}

async function selectTrace(traceId: string) {
  selectedTraceId.value = traceId
  selectedTraceItem.value = null
  loadingTrace.value = true
  errorMessage.value = ''
  try {
    selectedTraceItem.value = await getTraceItem(traceId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '溯源信息加载失败'
  } finally {
    loadingTrace.value = false
  }
}

function downloadCurrentDocument() {
  if (!docId.value) {
    return
  }
  window.open(downloadDocumentUrl(docId.value), '_blank')
}

function goBack() {
  if (preview.value?.task_id) {
    router.push(`/tasks/${preview.value.task_id}/results`)
    return
  }
  router.push('/tasks')
}
</script>

<style scoped>
.trace-page {
  background: #f5f7fa;
  min-height: 100vh;
}

.trace-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  min-height: calc(100vh - 73px);
}

.preview-pane {
  min-width: 0;
}

@media (max-width: 960px) {
  .trace-layout {
    grid-template-columns: 1fr;
  }
}
</style>
