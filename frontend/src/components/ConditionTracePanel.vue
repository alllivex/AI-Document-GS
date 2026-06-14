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
      <el-descriptions-item label="条件表达式">{{ businessExpression }}</el-descriptions-item>
      <el-descriptions-item label="计算结果">{{ trace.evaluated_result ? 'True' : 'False' }}</el-descriptions-item>
      <el-descriptions-item label="命中分支">{{ trace.selected_branch }}</el-descriptions-item>
      <el-descriptions-item label="理论输出">{{ trace.expected_output_text || '-' }}</el-descriptions-item>
      <el-descriptions-item label="实际输出">{{ trace.actual_output_text || '-' }}</el-descriptions-item>
    </el-descriptions>

    <section class="detail-block">
      <h4>参与字段</h4>
      <el-table :data="usedFieldRows" border size="small">
        <el-table-column label="字段名" min-width="180" prop="field_name" />
        <el-table-column label="数据值" min-width="120" prop="display_value" />
      </el-table>
    </section>

    <SourceRecordVerticalTable
      v-for="(record, index) in trace.source_records"
      :key="`${record.table_name}_${record.row_index}_${index}`"
      :record="record"
    />

    <el-collapse>
      <el-collapse-item title="高级信息" name="advanced">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="系统表达式">{{ trace.expression || '-' }}</el-descriptions-item>
          <el-descriptions-item label="参与变量路径">{{ trace.used_variables.join('、') || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SourceRecordVerticalTable from './SourceRecordVerticalTable.vue'
import type { ConditionTraceDetail, SourceRecordField } from '../types/trace'
import { getFieldDisplayName } from '../utils/displayName'

const props = defineProps<{
  trace: ConditionTraceDetail
}>()

const usedFieldsByPath = computed(() => {
  const map = new Map<string, SourceRecordField>()
  for (const record of props.trace.source_records) {
    for (const field of record.fields) {
      map.set(`${record.table_name}.${field.field_name}`, field)
    }
  }
  return map
})

const usedFieldRows = computed(() =>
  props.trace.used_variables.map((path) => {
    const field = usedFieldsByPath.value.get(path)
    return {
      field_name: field ? getFieldDisplayName(field) : path,
      display_value: field?.display_value || formatValue(field?.raw_value),
    }
  }),
)

const businessExpression = computed(() => {
  let expression = props.trace.expression || '-'
  for (const path of props.trace.used_variables) {
    const field = usedFieldsByPath.value.get(path)
    if (!field) {
      continue
    }
    expression = expression.split(path).join(getFieldDisplayName(field))
  }
  return expression
})

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  return String(value)
}
</script>

<style scoped>
.trace-section,
.trace-title,
.detail-block {
  display: grid;
  gap: 14px;
}

.detail-block h4 {
  font-size: 14px;
  margin: 0;
}
</style>
