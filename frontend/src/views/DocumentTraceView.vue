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

    <div class="trace-options">
      <el-switch
        v-model="showTraceHighlight"
        active-text="显示溯源高亮"
        inactive-text="隐藏溯源高亮"
      />
    </div>

    <section class="trace-layout">
      <div v-loading="loadingPreview" class="preview-pane">
        <PreviewRenderer
          :preview="preview"
          :selected-trace-id="selectedTraceId"
          :show-trace-highlight="showTraceHighlight"
          @select-trace="selectTrace"
        />
      </div>
      <TraceDetailPanel
        :trace-item="selectedTraceItem"
        :loading="loadingTrace"
        @select-trace="selectTrace"
        @locate-trace="locateTrace"
      />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DocumentNavBar from '../components/DocumentNavBar.vue'
import PreviewRenderer from '../components/PreviewRenderer.vue'
import TraceDetailPanel from '../components/TraceDetailPanel.vue'
import { downloadDocumentUrl, getDocumentPreview } from '../api/documents'
import { getTraceItem } from '../api/trace'
import type { TraceDetail } from '../types/trace'

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

const route = useRoute()
const router = useRouter()
const docId = computed(() => String(route.params.docId || ''))
const preview = ref<PreviewFile | null>(null)
const selectedTraceId = ref<string | null>(null)
const selectedTraceItem = ref<TraceDetail | null>(null)
const loadingPreview = ref(false)
const loadingTrace = ref(false)
const errorMessage = ref('')
const showTraceHighlight = ref(true)

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

async function locateTrace(traceId: string) {
  selectedTraceId.value = null
  await nextTick()
  selectedTraceId.value = traceId
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
  background:
    linear-gradient(180deg, rgba(238, 244, 255, 0.82), rgba(245, 247, 251, 0.92) 240px),
    var(--color-bg);
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--app-header-height, 60px));
  min-height: 0;
  overflow: hidden;
}

.trace-layout {
  align-items: start;
  display: grid;
  flex: 1;
  gap: 20px;
  grid-template-columns: minmax(0, 1fr) 430px;
  min-height: 0;
  overflow: hidden;
  padding: 20px 24px 24px;
}

.trace-options {
  align-items: center;
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
  padding: 10px 24px;
}

.preview-pane {
  height: 100%;
  min-width: 0;
  overflow-y: auto;
}

@media (max-width: 960px) {
  .trace-page {
    height: auto;
    min-height: calc(100vh - var(--app-header-height, 60px));
    overflow: visible;
  }

  .trace-layout {
    grid-template-columns: 1fr;
    overflow: visible;
    padding: 16px;
  }

  .preview-pane {
    height: auto;
    overflow-y: visible;
  }
}
</style>
