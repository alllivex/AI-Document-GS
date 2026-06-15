<template>
  <div class="preview-renderer" :class="{ 'hide-trace-highlight': !showTraceHighlight }">
    <el-empty v-if="!preview || !preview.blocks?.length" description="暂无预览内容" />

    <template v-else>
      <div v-if="showTraceHighlight" class="trace-legend">
        <span class="legend-item trace-field">字段来源</span>
        <span class="legend-item trace-condition">条件判断</span>
        <span class="legend-item trace-loop">循环表格</span>
        <span class="legend-item trace-ai">AI 生成</span>
      </div>
      <article ref="previewRoot" class="document-preview preview-paper">
        <template v-for="block in preview.blocks" :key="block.block_id">
          <component :is="headingTag(block.level)" v-if="block.type === 'heading'" class="preview-heading">
            {{ block.text }}
          </component>

          <p
            v-else-if="block.type === 'paragraph'"
            class="preview-paragraph"
            :class="[block.block_trace_id ? 'clickable-block' : '', traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
            :data-trace-id="block.block_trace_id || undefined"
            :style="styleToCss(block.style)"
            @click="selectBlockTrace(block.block_trace_id, $event)"
          >
            <button
              v-if="block.block_trace_id"
              class="block-trace-button"
              :class="[traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
              type="button"
              :data-trace-id="block.block_trace_id"
              @click.stop="selectTraceFromPreview(block.block_trace_id)"
            >
              {{ blockTraceLabel(block.block_trace_kind) }}
            </button>
            <template v-for="(run, index) in block.runs" :key="`${block.block_id}_${index}`">
              <button
                v-if="run.trace_id"
                class="trace-text"
                :class="[traceKindClass(run.trace_kind), { active: run.trace_id === selectedTraceId }]"
                type="button"
                :data-trace-id="run.trace_id"
                :style="styleToCss(run.style)"
                @click.stop="selectTraceFromPreview(run.trace_id)"
              >
                {{ run.text }}
              </button>
              <span v-else :style="styleToCss(run.style)">{{ run.text }}</span>
            </template>
          </p>

          <div
            v-else-if="block.type === 'table'"
            class="preview-table-wrap"
            :class="[block.block_trace_id ? 'clickable-block' : '', traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
            :data-trace-id="block.block_trace_id || undefined"
            @click.self="block.block_trace_id && selectTraceFromPreview(block.block_trace_id)"
          >
            <div v-if="block.block_trace_id" class="table-trace-toolbar">
              <el-button size="small" @click="selectTraceFromPreview(block.block_trace_id)">
                {{ blockTraceLabel(block.block_trace_kind) }}
              </el-button>
            </div>
            <table class="preview-table" :style="tableStyle(block)">
              <thead>
                <tr>
                  <th
                    v-for="(cell, index) in block.headers"
                    :key="`${block.block_id}_header_${index}`"
                    :colspan="cell.colspan || 1"
                    :rowspan="cell.rowspan || 1"
                    :style="cellStyle(cell)"
                    :data-trace-id="cell.trace_id || undefined"
                  >
                    <TraceCell
                      :cell="cell"
                      :selected-trace-id="selectedTraceId || undefined"
                      @select-trace="selectTraceFromPreview"
                    />
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!block.rows.length">
                  <td :colspan="Math.max(block.headers.length, 1)" class="empty-cell">暂无表格数据</td>
                </tr>
                <tr v-for="(row, rowIndex) in block.rows" :key="`${block.block_id}_row_${rowIndex}`">
                  <td
                    v-for="(cell, cellIndex) in row"
                    :key="`${block.block_id}_${rowIndex}_${cellIndex}`"
                    :colspan="cell.colspan || 1"
                    :rowspan="cell.rowspan || 1"
                    :style="cellStyle(cell)"
                    :data-trace-id="cell.trace_id || undefined"
                  >
                    <TraceCell
                      :cell="cell"
                      :selected-trace-id="selectedTraceId || undefined"
                      @select-trace="selectTraceFromPreview"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </article>
    </template>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, nextTick, ref, watch } from 'vue'

interface PreviewStyle {
  bold?: boolean | null
  italic?: boolean | null
  underline?: boolean | null
  alignment?: string | null
  color?: string | null
  background_color?: string | null
  font_size_pt?: number | null
}

interface PreviewRun {
  text: string
  trace_id: string | null
  trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
  ai_block_id?: string | null
  style?: PreviewStyle | null
}

interface PreviewTableCell {
  text: string
  trace_id: string | null
  trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
  ai_block_id?: string | null
  runs?: PreviewRun[] | null
  colspan?: number | null
  rowspan?: number | null
  style?: PreviewStyle | null
  width_px?: number | null
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
      block_trace_id?: string | null
      block_trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
      runs: PreviewRun[]
      style?: PreviewStyle | null
    }
  | {
      type: 'table'
      block_id: string
      block_trace_id?: string | null
      block_trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
      headers: PreviewTableCell[]
      rows: PreviewTableCell[][]
      style?: PreviewStyle | null
      width_px?: number | null
    }

interface PreviewFile {
  blocks?: PreviewBlock[]
}

const props = withDefaults(
  defineProps<{
    preview: PreviewFile | null
    selectedTraceId?: string | null
    showTraceHighlight?: boolean
  }>(),
  {
    selectedTraceId: null,
    showTraceHighlight: true,
  },
)

const emit = defineEmits<{
  'select-trace': [traceId: string]
}>()

const previewRoot = ref<HTMLElement | null>(null)
const suppressAutoScrollTraceId = ref<string | null>(null)

watch(
  () => props.selectedTraceId,
  async (traceId) => {
    if (!traceId) {
      return
    }
    if (suppressAutoScrollTraceId.value === traceId) {
      suppressAutoScrollTraceId.value = null
      return
    }
    await nextTick()
    scrollTraceIntoView(traceId)
  },
  { flush: 'post' },
)

const TraceCell = defineComponent({
  props: {
    cell: {
      type: Object,
      required: true,
    },
    selectedTraceId: {
      type: String,
      default: '',
    },
  },
  emits: ['select-trace'],
  setup(props, { emit }) {
    return () => {
      const cell = props.cell as PreviewTableCell
      const runs = cell.runs?.length ? cell.runs : [{ text: cell.text, trace_id: cell.trace_id, trace_kind: cell.trace_kind }]
      return h(
        'span',
        { class: 'trace-cell-content' },
        runs.map((run, index) => {
          if (!run.trace_id) {
            return h('span', { key: index, style: styleToCss(run.style) }, run.text)
          }
          const traceId = run.trace_id
          return h(
            'button',
            {
              key: index,
              class: ['trace-text', traceKindClass(run.trace_kind), { active: traceId === props.selectedTraceId }],
              type: 'button',
              'data-trace-id': traceId,
              style: styleToCss(run.style),
              onClick: () => emit('select-trace', traceId),
            },
            run.text,
          )
        }),
      )
    }
  },
})

function styleToCss(style?: PreviewStyle | null) {
  if (!style) {
    return undefined
  }
  const css: Record<string, string> = {}
  if (style.bold) {
    css.fontWeight = '700'
  }
  if (style.italic) {
    css.fontStyle = 'italic'
  }
  if (style.underline) {
    css.textDecoration = 'underline'
  }
  if (style.alignment) {
    css.textAlign = style.alignment
  }
  if (style.color) {
    css.color = normalizeHexColor(style.color)
  }
  if (style.background_color) {
    css.backgroundColor = normalizeHexColor(style.background_color)
  }
  if (style.font_size_pt) {
    css.fontSize = `${style.font_size_pt}pt`
  }
  return css
}

function tableStyle(block: Extract<PreviewBlock, { type: 'table' }>) {
  const css: Record<string, string> = {}
  if (block.width_px) {
    css.width = `${block.width_px}px`
    css.maxWidth = '100%'
  }
  return css
}

function cellStyle(cell: PreviewTableCell) {
  const css: Record<string, string> = {}
  Object.assign(css, styleToCss(cell.style))
  if (cell.width_px) {
    css.width = `${cell.width_px}px`
  }
  return css
}

function normalizeHexColor(value: string) {
  if (/^[0-9a-fA-F]{6}$/.test(value)) {
    return `#${value}`
  }
  return value
}

function scrollTraceIntoView(traceId: string) {
  const root = previewRoot.value
  if (!root) {
    return
  }
  const target = Array.from(root.querySelectorAll<HTMLElement>('[data-trace-id]')).find(
    (element) => element.dataset.traceId === traceId,
  )
  target?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' })
}

function headingTag(level?: number) {
  const safeLevel = Math.min(Math.max(level || 2, 1), 6)
  return `h${safeLevel}`
}

function traceKindClass(kind?: string | null) {
  return `trace-${kind || 'field'}`
}

function blockTraceLabel(kind?: string | null) {
  if (kind === 'ai') {
    return 'AI生成'
  }
  if (kind === 'loop') {
    return '查看表格循环溯源'
  }
  return '查看判断溯源'
}

function selectTraceFromPreview(traceId: string | null | undefined) {
  if (!traceId) {
    return
  }
  suppressAutoScrollTraceId.value = traceId
  emit('select-trace', traceId)
  window.setTimeout(() => {
    if (suppressAutoScrollTraceId.value === traceId) {
      suppressAutoScrollTraceId.value = null
    }
  }, 0)
}

function selectBlockTrace(traceId: string | null | undefined, event: MouseEvent) {
  if (!traceId) {
    return
  }
  const target = event.target as HTMLElement | null
  if (target?.closest('button')) {
    return
  }
  selectTraceFromPreview(traceId)
}
</script>

<style scoped>
.preview-renderer {
  align-items: flex-start;
  background: transparent;
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
  min-height: 100%;
  padding: 18px;
}

.trace-legend {
  align-items: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin: 0 auto;
  max-width: 860px;
  padding: 8px 10px;
  width: 100%;
}

.legend-item {
  border: 1px solid transparent;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 9px;
}

.document-preview {
  color: #242f42;
  line-height: 1.8;
}

.preview-paper {
  background:
    linear-gradient(90deg, rgba(36, 88, 211, 0.06) 0, transparent 5px),
    #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: 0 18px 46px rgba(20, 32, 56, 0.12);
  max-width: 794px;
  min-height: calc(100vh - 170px);
  padding: 48px 56px;
  width: 100%;
}

.preview-heading {
  line-height: 1.35;
  margin: 0 0 16px;
}

.preview-paragraph {
  border: 1px solid transparent;
  border-radius: 8px;
  margin: 0 0 12px;
  padding: 4px 6px;
  white-space: pre-wrap;
}

.preview-paragraph.clickable-block {
  cursor: pointer;
}

.preview-paragraph.trace-ai {
  border-color: #e9d5ff;
  background: #fcfaff;
}

.preview-paragraph.trace-ai.active {
  background: #f8f1ff;
}

.trace-text {
  background: #eef5ff;
  border: 1px solid #bdd4ff;
  border-radius: 6px;
  color: #1f4fbd;
  cursor: pointer;
  font: inherit;
  margin: 0 2px;
  padding: 1px 5px;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.trace-text:hover,
.trace-text.active {
  background: #2458d3;
  border-color: #2458d3;
  color: #fff !important;
}

.trace-field {
  background: #eef5ff;
  border-color: #bdd4ff;
  color: #1f4fbd;
}

.trace-condition {
  background: #f7edff;
  border-color: #dcbcff;
  color: #7a2bbf;
}

.trace-loop {
  background: #ebf8f1;
  border-color: #bfe8d5;
  color: #13794e;
}

.trace-ai {
  background: #fff5e6;
  border-color: #f7c978;
  color: #9b5a00;
}

.trace-condition:hover,
.trace-condition.active {
  background: #9333ea;
  color: #fff;
}

.trace-loop:hover,
.trace-loop.active {
  background: #16a34a;
  color: #fff;
}

.trace-ai:hover,
.trace-ai.active {
  background: #a16207;
  color: #fff;
}

.hide-trace-highlight .trace-text {
  background: transparent;
  border-color: transparent;
  color: inherit;
  margin: 0;
  padding: 0 1px;
  text-decoration: underline dotted rgba(36, 88, 211, 0.35);
  text-underline-offset: 3px;
}

.hide-trace-highlight .trace-text:hover,
.hide-trace-highlight .trace-text.active {
  background: #eef5ff;
  border-color: #bdd4ff;
  color: #1f4fbd !important;
}

.hide-trace-highlight .preview-paragraph.trace-ai {
  background: transparent;
  border-color: transparent;
}

.hide-trace-highlight .preview-table-wrap.clickable-block {
  border-color: var(--color-border);
}

.block-trace-button {
  border: 1px solid #d8b4fe;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  margin-right: 8px;
  padding: 3px 8px;
}

.preview-table-wrap {
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin: 16px 0;
  overflow-x: auto;
  padding: 10px;
}

.preview-table-wrap.clickable-block {
  border-color: #b7ebc6;
}

.preview-table-wrap.clickable-block.active {
  border-color: #16a34a;
}

.table-trace-toolbar {
  margin-bottom: 8px;
}

.preview-table {
  border-collapse: collapse;
  min-width: 420px;
  width: 100%;
}

.preview-table th,
.preview-table td {
  border: 1px solid var(--color-border);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview-table th {
  background: #f8fafc;
  color: #475467;
  font-weight: 600;
}

.empty-cell {
  color: #909399;
  text-align: center;
}

.trace-cell-content {
  white-space: pre-wrap;
}

@media (max-width: 760px) {
  .preview-renderer {
    padding: 0;
  }

  .preview-paper {
    padding: 24px 18px;
  }
}
</style>
