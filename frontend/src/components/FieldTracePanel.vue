<template>
  <div class="trace-section">
    <el-tag type="primary">字段溯源</el-tag>

    <el-descriptions :column="1" border>
      <el-descriptions-item label="数据表">{{ getTableDisplayName(trace) }}</el-descriptions-item>
      <el-descriptions-item label="字段">{{ getFieldDisplayName(trace) }}</el-descriptions-item>
      <el-descriptions-item label="模板变量">{{ getTemplateVarDisplayName(trace) }}</el-descriptions-item>
    </el-descriptions>

    <SourceRecordVerticalTable :record="trace.source_record" title="当前记录" />

    <el-collapse>
      <el-collapse-item title="高级信息" name="advanced">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="系统变量路径">{{ trace.canonical_var_path || trace.var_path }}</el-descriptions-item>
          <el-descriptions-item label="英文表名">{{ trace.table_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="英文字段名">{{ trace.field_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Excel列">{{ highlightedColumn || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SourceRecordVerticalTable from './SourceRecordVerticalTable.vue'
import type { FieldTraceDetail } from '../types/trace'
import { getFieldDisplayName, getTableDisplayName, getTemplateVarDisplayName } from '../utils/displayName'

const props = defineProps<{
  trace: FieldTraceDetail
}>()

const highlightedColumn = computed(() => {
  const highlighted = props.trace.source_record.fields.find((field) => field.is_highlighted)
  return highlighted?.excel_column_letter || null
})
</script>

<style scoped>
.trace-section {
  display: grid;
  gap: 14px;
}
</style>
