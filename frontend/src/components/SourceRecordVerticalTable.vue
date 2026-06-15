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
          <span
            :class="{ 'source-highlight-target': row.is_highlighted }"
            :data-field-name="row.field_name"
            :data-source-highlight-target="row.is_highlighted ? 'true' : undefined"
          >
            {{ getFieldDisplayName(row) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="数据值" min-width="180">
        <template #default="{ row }">
          <span
            :class="{ 'source-highlight-target': row.is_highlighted }"
            :data-field-name="row.field_name"
            :data-source-highlight-target="row.is_highlighted ? 'true' : undefined"
          >
            {{ row.display_value || formatValue(row.raw_value) }}
          </span>
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

.source-record :deep(.source-highlight-target) {
  border-radius: 4px;
  display: inline-block;
  padding: 2px 4px;
}

.source-record :deep(.source-highlight-focus) {
  box-shadow: 0 0 0 3px rgba(36, 88, 211, 0.24);
  outline: 2px solid rgba(36, 88, 211, 0.72);
}
</style>
