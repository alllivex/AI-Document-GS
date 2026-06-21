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

    <section ref="layoutRef" class="trace-layout" :style="layoutStyle">
      <div v-loading="loadingPreview" class="preview-pane">
        <PreviewRenderer
          :preview="preview"
          :selected-trace-id="selectedTraceId"
          :show-trace-highlight="showTraceHighlight"
          @select-trace="selectTrace"
        />
      </div>
      <div
        class="trace-resizer"
        role="separator"
        aria-label="调整文档预览和溯源详情宽度"
        aria-orientation="vertical"
        tabindex="0"
        @dblclick="resetDetailPaneWidth"
        @keydown="resizeWithKeyboard"
        @pointerdown="startResize"
      />
      <TraceDetailPanel
        class="trace-detail-pane"
        :trace-item="selectedTraceItem"
        :loading="loadingTrace"
        @select-trace="selectTrace"
        @locate-trace="locateTrace"
      />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
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
const layoutRef = ref<HTMLElement | null>(null)
const detailPaneWidth = ref(430)
const isResizing = ref(false)

const DEFAULT_DETAIL_PANE_WIDTH = 430
const MIN_PREVIEW_PANE_WIDTH = 420
const MIN_DETAIL_PANE_WIDTH = 320
const RESIZER_WIDTH = 10
const GRID_GAP_WIDTH = 16

const layoutStyle = computed(() => ({
  '--trace-detail-width': `${detailPaneWidth.value}px`,
}))

onMounted(loadPreview)
onBeforeUnmount(stopResize)

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

function startResize(event: PointerEvent) {
  if (window.matchMedia('(max-width: 960px)').matches) {
    return
  }

  isResizing.value = true
  document.body.classList.add('trace-resizing')
  updateDetailPaneWidth(event.clientX)
  window.addEventListener('pointermove', handleResize)
  window.addEventListener('pointerup', stopResize)
  window.addEventListener('pointercancel', stopResize)
}

function handleResize(event: PointerEvent) {
  if (!isResizing.value) {
    return
  }
  updateDetailPaneWidth(event.clientX)
}

function stopResize() {
  if (!isResizing.value) {
    return
  }
  isResizing.value = false
  document.body.classList.remove('trace-resizing')
  window.removeEventListener('pointermove', handleResize)
  window.removeEventListener('pointerup', stopResize)
  window.removeEventListener('pointercancel', stopResize)
}

function updateDetailPaneWidth(pointerX: number) {
  const layout = layoutRef.value
  if (!layout) {
    return
  }

  const rect = layout.getBoundingClientRect()
  const maxDetailWidth = rect.width - MIN_PREVIEW_PANE_WIDTH - RESIZER_WIDTH - GRID_GAP_WIDTH * 2
  const nextWidth = rect.right - pointerX - GRID_GAP_WIDTH
  detailPaneWidth.value = clamp(nextWidth, MIN_DETAIL_PANE_WIDTH, Math.max(MIN_DETAIL_PANE_WIDTH, maxDetailWidth))
}

function resizeWithKeyboard(event: KeyboardEvent) {
  if (window.matchMedia('(max-width: 960px)').matches) {
    return
  }

  const step = event.shiftKey ? 48 : 24
  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    setDetailPaneWidth(detailPaneWidth.value + step)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    setDetailPaneWidth(detailPaneWidth.value - step)
  } else if (event.key === 'Home') {
    event.preventDefault()
    setDetailPaneWidth(MIN_DETAIL_PANE_WIDTH)
  } else if (event.key === 'End') {
    event.preventDefault()
    setDetailPaneWidth(getMaxDetailPaneWidth())
  } else if (event.key === 'Enter') {
    event.preventDefault()
    resetDetailPaneWidth()
  }
}

function resetDetailPaneWidth() {
  setDetailPaneWidth(DEFAULT_DETAIL_PANE_WIDTH)
}

function setDetailPaneWidth(width: number) {
  detailPaneWidth.value = clamp(width, MIN_DETAIL_PANE_WIDTH, getMaxDetailPaneWidth())
}

function getMaxDetailPaneWidth() {
  const layout = layoutRef.value
  if (!layout) {
    return DEFAULT_DETAIL_PANE_WIDTH
  }
  return Math.max(
    MIN_DETAIL_PANE_WIDTH,
    layout.getBoundingClientRect().width - MIN_PREVIEW_PANE_WIDTH - RESIZER_WIDTH - GRID_GAP_WIDTH * 2,
  )
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
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
  gap: 0 8px;
  grid-template-columns: minmax(420px, 1fr) 10px minmax(320px, var(--trace-detail-width));
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

.trace-resizer {
  align-self: stretch;
  cursor: col-resize;
  min-height: 0;
  position: relative;
  touch-action: none;
}

.trace-resizer::before {
  background: rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  bottom: 10px;
  content: '';
  left: 50%;
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  transition:
    background 0.16s ease,
    width 0.16s ease;
  width: 2px;
}

.trace-resizer:hover::before,
.trace-resizer:focus-visible::before {
  background: var(--color-primary);
  width: 4px;
}

.trace-resizer:focus-visible {
  border-radius: 999px;
  outline: 2px solid rgba(36, 88, 211, 0.28);
  outline-offset: 2px;
}

.trace-detail-pane {
  min-width: 0;
}

:global(.trace-resizing) {
  cursor: col-resize;
  user-select: none;
}

@media (max-width: 960px) {
  .trace-page {
    height: auto;
    min-height: calc(100vh - var(--app-header-height, 60px));
    overflow: visible;
  }

  .trace-layout {
    grid-template-columns: 1fr;
    gap: 16px;
    overflow: visible;
    padding: 16px;
  }

  .preview-pane {
    height: auto;
    overflow-y: visible;
  }

  .trace-resizer {
    display: none;
  }
}
</style>
