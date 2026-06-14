<template>
  <div class="source-record">
    <div class="record-meta">
      <span>{{ displayName(record.table_name_cn, record.table_name) }}</span>
      <span>{{ record.source_file }}</span>
      <span>Excel 第 {{ record.excel_row_number }} 行</span>
    </div>

    <el-table :data="record.fields" border size="small" row-key="field_name" :row-class-name="rowClassName">
      <el-table-column label="字段名" min-width="180">
        <template #default="{ row }">
          {{ displayName(row.field_name_cn, row.field_name) }}
        </template>
      </el-table-column>
      <el-table-column label="数据值" min-width="180">
        <template #default="{ row }">
          {{ row.display_value || formatValue(row.raw_value) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { SourceRecordField, SourceRecordView } from '../types/trace'

defineProps<{
  record: SourceRecordView
}>()

function rowClassName({ row }: { row: SourceRecordField }) {
  return row.is_highlighted ? `trace-highlight-row highlight-row highlight-${row.highlight_reason}` : ''
}

function displayName(cn?: string, name?: string) {
  if (cn && name) {
    return `${cn}（${name}）`
  }
  return cn || name || '-'
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  return String(value)
}
</script>

<style scoped>
.source-record {
  display: grid;
  gap: 8px;
}

.record-meta {
  color: #606266;
  display: flex;
  flex-wrap: wrap;
  font-size: 12px;
  gap: 10px;
}

.source-record :deep(.highlight-row td) {
  background: #fff7d6 !important;
  font-weight: 600;
}

.source-record :deep(.highlight-used_in_condition td) {
  background: #f3e8ff !important;
}

.source-record :deep(.highlight-used_in_loop td) {
  background: #e8f7ee !important;
}
</style>
