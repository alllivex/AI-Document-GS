<template>
  <div class="trace-section">
    <el-tag type="success">表格循环溯源</el-tag>

    <el-descriptions :column="1" border>
      <el-descriptions-item label="来源表">{{ getTableDisplayName(trace) }}</el-descriptions-item>
      <el-descriptions-item label="匹配记录数">{{ trace.matched_row_count }}</el-descriptions-item>
      <el-descriptions-item label="使用字段">{{ usedFieldNames.join('、') || '-' }}</el-descriptions-item>
    </el-descriptions>

    <SourceRecordVerticalTable
      v-for="(record, index) in trace.source_records"
      :key="`${record.table_name}_${record.row_index}_${index}`"
      :record="record"
      :title="`第${index + 1}条记录`"
    />

    <el-collapse>
      <el-collapse-item title="高级信息" name="advanced">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="系统表名">{{ trace.table_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="循环变量">{{ trace.loop_alias || '-' }}</el-descriptions-item>
          <el-descriptions-item label="使用字段路径">{{ trace.used_fields.join('、') || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SourceRecordVerticalTable from './SourceRecordVerticalTable.vue'
import type { LoopTraceDetail, SourceRecordField } from '../types/trace'
import { getFieldDisplayName, getTableDisplayName } from '../utils/displayName'

const props = defineProps<{
  trace: LoopTraceDetail
}>()

const fieldsByPath = computed(() => {
  const map = new Map<string, SourceRecordField>()
  for (const record of props.trace.source_records) {
    for (const field of record.fields) {
      const path = `${record.table_name}.${field.field_name}`
      if (!map.has(path)) {
        map.set(path, field)
      }
    }
  }
  return map
})

const usedFieldNames = computed(() =>
  props.trace.used_fields.map((path) => {
    const field = fieldsByPath.value.get(path)
    return field ? getFieldDisplayName(field) : path
  }),
)
</script>

<style scoped>
.trace-section {
  display: grid;
  gap: 14px;
}
</style>
