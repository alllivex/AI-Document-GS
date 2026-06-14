<template>
  <aside class="trace-panel">
    <h3>溯源详情</h3>

    <el-empty v-if="!traceItem && !loading" description="点击左侧高亮文本查看来源" />
    <el-skeleton v-else-if="loading" :rows="7" animated />

    <template v-else-if="traceItem">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="来源表">
          {{ displayName(traceItem.table_name_cn, traceItem.table_name) }}
        </el-descriptions-item>
        <el-descriptions-item label="来源字段">
          {{ displayName(traceItem.field_name_cn, traceItem.field_name) }}
        </el-descriptions-item>
        <el-descriptions-item label="来源文件">
          {{ traceItem.source_file || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Excel 行号">
          {{ traceItem.excel_row_number ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Excel 列">
          {{ traceItem.excel_column_letter || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="原始值">
          {{ formatValue(traceItem.raw_value) }}
        </el-descriptions-item>
        <el-descriptions-item label="展示值">
          {{ traceItem.display_value || '-' }}
        </el-descriptions-item>
      </el-descriptions>

      <div class="source-row-section">
        <h4>来源行</h4>
        <SourceRowTable :trace-item="traceItem" />
      </div>
    </template>
  </aside>
</template>

<script setup lang="ts">
import SourceRowTable from './SourceRowTable.vue'

interface TraceItem {
  table_name?: string
  table_name_cn?: string
  field_name?: string
  field_name_cn?: string
  source_file?: string
  excel_row_number?: number
  excel_column_letter?: string | null
  raw_value?: unknown
  display_value?: string
}

defineProps<{
  traceItem: TraceItem | null
  loading?: boolean
}>()

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
.trace-panel {
  background: #fff;
  border-left: 1px solid #e4e7ed;
  min-height: 100%;
  padding: 20px;
}

.trace-panel h3 {
  font-size: 16px;
  margin: 0 0 16px;
}

.source-row-section {
  margin-top: 20px;
}

.source-row-section h4 {
  font-size: 14px;
  margin: 0 0 10px;
}
</style>
