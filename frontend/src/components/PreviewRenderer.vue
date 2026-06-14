<template>
  <div class="preview-renderer">
    <el-empty v-if="!preview || !preview.blocks?.length" description="暂无预览内容" />

    <template v-else>
      <article class="document-preview">
        <template v-for="block in preview.blocks" :key="block.block_id">
          <component :is="headingTag(block.level)" v-if="block.type === 'heading'" class="preview-heading">
            {{ block.text }}
          </component>

          <p
            v-else-if="block.type === 'paragraph'"
            class="preview-paragraph"
            :class="[block.block_trace_id ? 'clickable-block' : '', traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
            @click="selectBlockTrace(block.block_trace_id, $event)"
          >
            <button
              v-if="block.block_trace_id"
              class="block-trace-button"
              :class="[traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
              type="button"
              @click.stop="emit('select-trace', block.block_trace_id)"
            >
              {{ blockTraceLabel(block.block_trace_kind) }}
            </button>
            <template v-for="(run, index) in block.runs" :key="`${block.block_id}_${index}`">
              <button
                v-if="run.trace_id"
                class="trace-text"
                :class="[traceKindClass(run.trace_kind), { active: run.trace_id === selectedTraceId }]"
                type="button"
                @click.stop="emit('select-trace', run.trace_id)"
              >
                {{ run.text }}
              </button>
              <span v-else>{{ run.text }}</span>
            </template>
          </p>

          <div
            v-else-if="block.type === 'table'"
            class="preview-table-wrap"
            :class="[block.block_trace_id ? 'clickable-block' : '', traceKindClass(block.block_trace_kind), { active: block.block_trace_id === selectedTraceId }]"
            @click.self="block.block_trace_id && emit('select-trace', block.block_trace_id)"
          >
            <div v-if="block.block_trace_id" class="table-trace-toolbar">
              <el-button size="small" type="success" @click="emit('select-trace', block.block_trace_id)">
                {{ blockTraceLabel(block.block_trace_kind) }}
              </el-button>
            </div>
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-for="(cell, index) in block.headers" :key="`${block.block_id}_header_${index}`">
                    <TraceCell
                      :cell="cell"
                      :selected-trace-id="selectedTraceId || undefined"
                      @select-trace="emit('select-trace', $event)"
                    />
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!block.rows.length">
                  <td :colspan="Math.max(block.headers.length, 1)" class="empty-cell">暂无表格数据</td>
                </tr>
                <tr v-for="(row, rowIndex) in block.rows" :key="`${block.block_id}_row_${rowIndex}`">
                  <td v-for="(cell, cellIndex) in row" :key="`${block.block_id}_${rowIndex}_${cellIndex}`">
                    <TraceCell
                      :cell="cell"
                      :selected-trace-id="selectedTraceId || undefined"
                      @select-trace="emit('select-trace', $event)"
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
import { defineComponent, h } from 'vue'

interface PreviewRun {
  text: string
  trace_id: string | null
  trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
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
  trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
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
      block_trace_id?: string | null
      block_trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
      runs: PreviewRun[]
    }
  | {
      type: 'table'
      block_id: string
      block_trace_id?: string | null
      block_trace_kind?: 'field' | 'condition' | 'loop' | 'ai' | null
      headers: PreviewTableCell[]
      rows: PreviewTableCell[][]
    }

interface PreviewFile {
  blocks?: PreviewBlock[]
}

defineProps<{
  preview: PreviewFile | null
  selectedTraceId?: string | null
}>()

const emit = defineEmits<{
  'select-trace': [traceId: string]
}>()

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
      if (!cell.trace_id) {
        return h('span', cell.text)
      }
      return h(
        'button',
        {
          class: ['trace-text', traceKindClass(cell.trace_kind), { active: cell.trace_id === props.selectedTraceId }],
          type: 'button',
          onClick: () => emit('select-trace', cell.trace_id),
        },
        cell.text,
      )
    }
  },
})

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

function selectBlockTrace(traceId: string | null | undefined, event: MouseEvent) {
  if (!traceId) {
    return
  }
  const target = event.target as HTMLElement | null
  if (target?.closest('button')) {
    return
  }
  emit('select-trace', traceId)
}
</script>

<style scoped>
.preview-renderer {
  background: #fff;
  min-height: 100%;
  padding: 24px;
}

.document-preview {
  color: #303133;
  line-height: 1.8;
  max-width: 920px;
}

.preview-heading {
  line-height: 1.35;
  margin: 0 0 16px;
}

.preview-paragraph {
  border: 1px solid transparent;
  border-radius: 6px;
  margin: 0 0 12px;
  padding: 2px 4px;
}

.preview-paragraph.clickable-block {
  cursor: pointer;
}

.preview-paragraph.trace-ai {
  border-color: #e9d5ff;
}

.preview-paragraph.trace-ai.active {
  background: #faf5ff;
}

.trace-text {
  background: #ecf5ff;
  border: 1px solid transparent;
  border-radius: 4px;
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  margin: 0 2px;
  padding: 0 3px;
}

.trace-text:hover,
.trace-text.active {
  background: #409eff;
  color: #fff;
}

.trace-condition {
  background: #f3e8ff;
  color: #7e22ce;
}

.trace-loop {
  background: #e8f7ee;
  color: #15803d;
}

.trace-ai {
  background: #f5f3ff;
  color: #6d28d9;
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
  background: #7c3aed;
  color: #fff;
}

.block-trace-button {
  border: 1px solid #d8b4fe;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-right: 8px;
  padding: 2px 6px;
}

.preview-table-wrap {
  border: 1px solid transparent;
  border-radius: 6px;
  margin: 16px 0;
  overflow-x: auto;
  padding: 8px;
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
  border: 1px solid #dcdfe6;
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.preview-table th {
  background: #f5f7fa;
  font-weight: 600;
}

.empty-cell {
  color: #909399;
  text-align: center;
}
</style>
