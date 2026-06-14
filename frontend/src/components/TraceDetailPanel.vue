<template>
  <aside ref="panelRef" class="trace-panel">
    <h3>溯源详情</h3>

    <el-empty v-if="!traceItem && !loading" description="点击左侧高亮文本查看来源" />
    <el-skeleton v-else-if="loading" :rows="7" animated />

    <template v-else-if="traceItem">
      <FieldTracePanel v-if="traceItem.trace_kind === 'field'" :trace="traceItem" />
      <ConditionTracePanel v-else-if="traceItem.trace_kind === 'condition'" :trace="traceItem" />
      <LoopTracePanel v-else-if="traceItem.trace_kind === 'loop'" :trace="traceItem" />
      <AITracePanel v-else-if="traceItem.trace_kind === 'ai'" :trace="traceItem" @select-trace="$emit('select-trace', $event)" />
      <el-alert v-else title="暂不支持该溯源类型" type="warning" :closable="false" />
    </template>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import AITracePanel from './AITracePanel.vue'
import ConditionTracePanel from './ConditionTracePanel.vue'
import FieldTracePanel from './FieldTracePanel.vue'
import LoopTracePanel from './LoopTracePanel.vue'
import type { TraceDetail } from '../types/trace'

const props = defineProps<{
  traceItem: TraceDetail | null
  loading?: boolean
}>()

defineEmits<{
  'select-trace': [traceId: string]
}>()

const panelRef = ref<HTMLElement | null>(null)
let scrollRequestId = 0

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
  background: #fff;
  border-left: 1px solid #e4e7ed;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
}

.trace-panel h3 {
  font-size: 16px;
  margin: 0 0 16px;
}

@media (max-width: 960px) {
  .trace-panel {
    border-left: 0;
    border-top: 1px solid #e4e7ed;
    height: auto;
    max-height: none;
    overflow-y: visible;
  }
}
</style>
