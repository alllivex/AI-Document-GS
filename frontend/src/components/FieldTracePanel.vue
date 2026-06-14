<template>
  <div class="trace-section">
    <el-tag type="primary">字段溯源</el-tag>
    <el-descriptions :column="1" border>
      <el-descriptions-item label="数据表">{{ displayName(trace.table_name_cn, trace.table_name) }}</el-descriptions-item>
      <el-descriptions-item label="字段">{{ displayName(trace.field_name_cn, trace.field_name) }}</el-descriptions-item>
      <el-descriptions-item label="变量路径">{{ trace.var_path }}</el-descriptions-item>
    </el-descriptions>
    <SourceRecordVerticalTable :record="trace.source_record" />
  </div>
</template>

<script setup lang="ts">
import SourceRecordVerticalTable from './SourceRecordVerticalTable.vue'
import type { FieldTraceDetail } from '../types/trace'

defineProps<{
  trace: FieldTraceDetail
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
