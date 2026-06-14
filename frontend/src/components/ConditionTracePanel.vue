<template>
  <div class="trace-section">
    <div class="trace-title">
      <el-tag type="warning">条件判断溯源</el-tag>
      <el-alert
        v-if="!trace.is_consistent"
        title="理论输出与实际输出不一致"
        type="error"
        show-icon
        :closable="false"
      />
    </div>

    <el-descriptions :column="1" border>
      <el-descriptions-item label="条件表达式">{{ trace.expression }}</el-descriptions-item>
      <el-descriptions-item label="参与变量">{{ trace.used_variables.join('、') || '-' }}</el-descriptions-item>
      <el-descriptions-item label="计算结果">{{ trace.evaluated_result ? 'True' : 'False' }}</el-descriptions-item>
      <el-descriptions-item label="命中分支">{{ trace.selected_branch }}</el-descriptions-item>
      <el-descriptions-item label="理论输出">{{ trace.expected_output_text || '-' }}</el-descriptions-item>
      <el-descriptions-item label="实际输出">{{ trace.actual_output_text || '-' }}</el-descriptions-item>
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
import type { ConditionTraceDetail } from '../types/trace'

defineProps<{
  trace: ConditionTraceDetail
}>()
</script>

<style scoped>
.trace-section,
.trace-title {
  display: grid;
  gap: 14px;
}
</style>
