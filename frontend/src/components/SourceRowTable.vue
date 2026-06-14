<template>
  <el-table :data="rows" border size="small" class="source-row-table">
    <el-table-column prop="excel_row_number" label="Excel行" width="90" />
    <el-table-column :label="fieldLabel" min-width="180">
      <template #default="{ row }">
        <span class="highlighted-field">{{ row.value }}</span>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TraceItem {
  field_name?: string
  field_name_cn?: string
  excel_row_number?: number
  raw_value?: unknown
  display_value?: string
}

const props = defineProps<{
  traceItem: TraceItem
}>()

const fieldLabel = computed(() => {
  const cn = props.traceItem.field_name_cn
  const name = props.traceItem.field_name
  if (cn && name) {
    return `${cn}（${name}）`
  }
  return cn || name || '当前字段'
})

const rows = computed(() => [
  {
    excel_row_number: props.traceItem.excel_row_number ?? '-',
    value: props.traceItem.display_value || formatValue(props.traceItem.raw_value),
  },
])

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  return String(value)
}
</script>

<style scoped>
.source-row-table :deep(.highlighted-field) {
  background: #fff3cd;
  border-radius: 4px;
  color: #7a4d00;
  display: inline-block;
  font-weight: 600;
  padding: 2px 6px;
}
</style>
