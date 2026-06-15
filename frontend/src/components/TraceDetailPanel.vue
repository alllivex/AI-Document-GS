<template>
  <aside ref="panelRef" class="trace-panel">
    <div class="panel-heading">
      <div>
        <span class="panel-eyebrow">Evidence Panel</span>
        <h3>溯源详情</h3>
      </div>
      <span v-if="traceItem" class="kind-pill" :class="`kind-${kindMeta.tone}`">{{ kindMeta.label }}</span>
    </div>

    <el-empty v-if="!traceItem && !loading" description="点击左侧高亮文本查看来源" />
    <el-skeleton v-else-if="loading" :rows="7" animated />

    <template v-else-if="traceItem">
      <section class="trace-summary" :class="`summary-${kindMeta.tone}`">
        <strong>{{ summaryTitle }}</strong>
        <span>{{ kindMeta.description }}</span>
        <p>{{ summaryText }}</p>
      </section>

      <FieldTracePanel v-if="traceItem.trace_kind === 'field'" :trace="traceItem" />
      <ConditionTracePanel v-else-if="traceItem.trace_kind === 'condition'" :trace="traceItem" />
      <LoopTracePanel v-else-if="traceItem.trace_kind === 'loop'" :trace="traceItem" />
      <AITracePanel v-else-if="traceItem.trace_kind === 'ai'" :trace="traceItem" @select-trace="$emit('select-trace', $event)" />
      <el-alert v-else title="暂不支持该溯源类型" type="warning" :closable="false" />
    </template>
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import AITracePanel from './AITracePanel.vue'
import ConditionTracePanel from './ConditionTracePanel.vue'
import FieldTracePanel from './FieldTracePanel.vue'
import LoopTracePanel from './LoopTracePanel.vue'
import type { TraceDetail } from '../types/trace'
import { traceKindMeta } from '../utils/uiMeta'

const props = defineProps<{
  traceItem: TraceDetail | null
  loading?: boolean
}>()

defineEmits<{
  'select-trace': [traceId: string]
}>()

const panelRef = ref<HTMLElement | null>(null)
let scrollRequestId = 0

const kindMeta = computed(() => traceKindMeta(props.traceItem?.trace_kind || 'field'))

const summaryTitle = computed(() => {
  if (!props.traceItem) {
    return ''
  }
  if (props.traceItem.trace_kind === 'field') {
    return `${props.traceItem.table_name_cn || props.traceItem.table_name}.${props.traceItem.field_name_cn || props.traceItem.field_name}`
  }
  if (props.traceItem.trace_kind === 'condition') {
    return props.traceItem.evaluated_result ? '条件成立' : '条件不成立'
  }
  if (props.traceItem.trace_kind === 'loop') {
    return `${props.traceItem.table_name_cn || props.traceItem.table_name}，匹配 ${props.traceItem.matched_row_count} 行`
  }
  return `${props.traceItem.block_id} · ${props.traceItem.status}`
})

const summaryText = computed(() => {
  if (!props.traceItem) {
    return ''
  }
  if (props.traceItem.trace_kind === 'field') {
    return `来源文件 ${props.traceItem.source_record.source_file}，Excel 第 ${props.traceItem.source_record.excel_row_number} 行。`
  }
  if (props.traceItem.trace_kind === 'condition') {
    return `表达式：${props.traceItem.expression}，输出分支：${props.traceItem.selected_branch}。`
  }
  if (props.traceItem.trace_kind === 'loop') {
    return `循环别名 ${props.traceItem.loop_alias}，使用字段 ${props.traceItem.used_fields.join('、') || '无'}。`
  }
  return props.traceItem.error_message || `模型 ${props.traceItem.model || '-'} 生成，输入变量 ${props.traceItem.input_variables.length} 个。`
})

watch(
  () => [props.traceItem?.trace_id, props.loading] as const,
  async () => {
    const requestId = ++scrollRequestId
    await nextTick()

    if (requestId !== scrollRequestId || props.loading) {
      return
    }

    scrollToHighlightedRow()
  },
  { flush: 'post' },
)

function scrollToHighlightedRow() {
  const panel = panelRef.value
  if (!panel) {
    return
  }

  const highlightedRow = panel.querySelector<HTMLElement>('.trace-highlight-row, .highlight-row')
  if (!highlightedRow) {
    panel.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }

  highlightedRow.scrollIntoView({
    block: 'center',
    inline: 'nearest',
    behavior: 'smooth',
  })
}
</script>

<style scoped>
.trace-panel {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding: 18px;
}

.panel-heading {
  align-items: flex-start;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  gap: 12px;
  justify-content: space-between;
  margin: -2px 0 16px;
  padding-bottom: 14px;
}

.panel-eyebrow {
  color: var(--color-primary);
  display: block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin-bottom: 3px;
  text-transform: uppercase;
}

.trace-panel h3 {
  color: var(--color-text);
  font-size: 17px;
  font-weight: 750;
  margin: 0;
}

.kind-pill {
  border: 1px solid transparent;
  border-radius: 999px;
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 800;
  padding: 6px 9px;
}

.kind-field {
  background: #eef5ff;
  border-color: #bdd4ff;
  color: #1f4fbd;
}

.kind-condition {
  background: #f7edff;
  border-color: #dcbcff;
  color: #7a2bbf;
}

.kind-loop {
  background: #ebf8f1;
  border-color: #bfe8d5;
  color: #13794e;
}

.kind-ai {
  background: #fff5e6;
  border-color: #f7c978;
  color: #9b5a00;
}

.trace-summary {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  margin-bottom: 16px;
  padding: 14px;
}

.trace-summary strong {
  color: var(--color-text);
  font-size: 15px;
}

.trace-summary span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.trace-summary p {
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0;
  overflow-wrap: anywhere;
}

.summary-field {
  background: #f7fbff;
}

.summary-condition {
  background: #fcf8ff;
}

.summary-loop {
  background: #f6fcf9;
}

.summary-ai {
  background: #fffaf0;
}

@media (max-width: 960px) {
  .trace-panel {
    border-radius: 8px;
    height: auto;
    max-height: none;
    overflow-y: visible;
  }
}
</style>
