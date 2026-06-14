<template>
  <div class="preview-renderer">
    <el-empty v-if="!preview || !preview.blocks?.length" description="暂无预览内容" />

    <template v-else>
      <article class="document-preview">
        <template v-for="block in preview.blocks" :key="block.block_id">
          <component :is="headingTag(block.level)" v-if="block.type === 'heading'" class="preview-heading">
            {{ block.text }}
          </component>

          <p v-else-if="block.type === 'paragraph'" class="preview-paragraph">
            <template v-for="(run, index) in block.runs" :key="`${block.block_id}_${index}`">
              <button
                v-if="run.trace_id"
                class="trace-text"
                :class="{ active: run.trace_id === selectedTraceId }"
                type="button"
                @click="$emit('select-trace', run.trace_id)"
              >
                {{ run.text }}
              </button>
              <span v-else>{{ run.text }}</span>
            </template>
          </p>

          <div v-else-if="block.type === 'table'" class="preview-table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-for="(cell, index) in block.headers" :key="`${block.block_id}_header_${index}`">
                    <TraceCell
                      :cell="cell"
                      :selected-trace-id="selectedTraceId || undefined"
                      @select-trace="$emit('select-trace', $event)"
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
                      @select-trace="$emit('select-trace', $event)"
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

interface PreviewFile {
  blocks?: PreviewBlock[]
}

defineProps<{
  preview: PreviewFile | null
  selectedTraceId?: string | null
}>()

defineEmits<{
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
          class: ['trace-text', { active: cell.trace_id === props.selectedTraceId }],
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
  margin: 0 0 12px;
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

.preview-table-wrap {
  margin: 16px 0;
  overflow-x: auto;
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
