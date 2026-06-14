<template>
  <section class="source-record">
    <h4 v-if="title">{{ title }}</h4>
    <div class="record-meta">
      <span>来源记录：{{ getTableDisplayName(record) }}</span>
      <span>来源文件：{{ record.source_file || '-' }}</span>
      <span>Excel位置：第{{ record.excel_row_number }}行</span>
    </div>

    <el-table :data="record.fields" border size="small" row-key="field_name" :row-class-name="rowClassName">
      <el-table-column label="字段名" min-width="180">
        <template #default="{ row }">
          {{ getFieldDisplayName(row) }}
        </template>
      </el-table-column>
      <el-table-column label="数据值" min-width="180">
        <template #default="{ row }">
          {{ row.display_value || formatValue(row.raw_value) }}
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { SourceRecordField, SourceRecordView } from '../types/trace'
import { getFieldDisplayName, getTableDisplayName } from '../utils/displayName'

defineProps<{
  record: SourceRecordView
  title?: string
}>()

function rowClassName({ row }: { row: SourceRecordField }) {
  return row.is_highlighted ? `trace-highlight-row highlight-row highlight-${row.highlight_reason}` : ''
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

.source-record h4 {
  font-size: 14px;
  margin: 0;
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
