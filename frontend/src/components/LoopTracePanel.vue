<template>
  <div class="trace-section">
    <el-tag type="success">表格循环溯源</el-tag>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="来源表">{{ displayName(trace.table_name_cn, trace.table_name) }}</el-descriptions-item>
      <el-descriptions-item label="循环变量">{{ trace.loop_alias }}</el-descriptions-item>
      <el-descriptions-item label="匹配记录数">{{ trace.matched_row_count }}</el-descriptions-item>
      <el-descriptions-item label="使用字段">{{ trace.used_fields.join('、') || '-' }}</el-descriptions-item>
    </el-descriptions>

    <SourceRecordVerticalTable
      v-for="(record, index) in trace.source_records"
      :key="`${record.table_name}_${record.row_index}_${index}`"
      :record="record"
    />
  </div>
</template>

<script setup lang="ts">
import SourceRecordVerticalTable from './SourceRecordVerticalTable.vue'
import type { LoopTraceDetail } from '../types/trace'

defineProps<{
  trace: LoopTraceDetail
}>()

function displayName(cn?: string, name?: string) {
  if (cn && name) {
    return `${cn}（${name}）`
  }
  return cn || name || '-'
}
</script>

<style scoped>
.trace-section {
  display: grid;
  gap: 14px;
}
</style>
