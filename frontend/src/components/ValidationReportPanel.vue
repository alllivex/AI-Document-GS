<template>
  <div>
    <el-empty v-if="!report && !loading" description="尚未校验" />
    <el-skeleton v-else-if="loading" :rows="4" animated />

    <template v-else-if="report">
      <el-alert
        :title="statusTitle"
        :type="report.status === 'failed' ? 'error' : report.status === 'passed_with_warnings' ? 'warning' : 'success'"
        show-icon
        :closable="false"
      />

      <div class="summary">
        <div class="summary-item danger">
          <span>错误</span>
          <strong>{{ report.summary.error_count }}</strong>
        </div>
        <div class="summary-item warning">
          <span>警告</span>
          <strong>{{ report.summary.warning_count }}</strong>
        </div>
        <div class="summary-item default">
          <span>提示</span>
          <strong>{{ report.summary.info_count }}</strong>
        </div>
      </div>

      <el-table :data="report.items" border>
        <el-table-column label="级别" width="100">
          <template #default="{ row }">
            <StatusTag :type="levelType(row.level)" :label="levelText(row.level)" />
          </template>
        </el-table-column>
        <el-table-column prop="code" label="代码" width="180" />
        <el-table-column prop="message" label="信息" min-width="260" />
        <el-table-column label="位置" min-width="180">
          <template #default="{ row }">
            {{ [row.table_name, row.field_name].filter(Boolean).join('.') || row.template_file || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="suggestion" label="建议" min-width="220" />
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from './common/StatusTag.vue'
import type { ValidateTaskResponse, ValidationLevel } from '../types/validation'

const props = defineProps<{
  report: ValidateTaskResponse | null
  loading?: boolean
}>()

const statusTitle = computed(() => {
  if (!props.report) {
    return ''
  }
  if (props.report.status === 'failed') {
    return '校验失败'
  }
  if (props.report.status === 'passed_with_warnings') {
    return '校验通过，但存在警告'
  }
  return '校验通过'
})

function levelType(level: ValidationLevel): 'danger' | 'warning' | 'default' {
  if (level === 'error') {
    return 'danger'
  }
  if (level === 'warning') {
    return 'warning'
  }
  return 'default'
}

function levelText(level: ValidationLevel) {
  return level === 'error' ? '错误' : level === 'warning' ? '警告' : '提示'
}
</script>

<style scoped>
.summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 12px 0;
}

.summary-item {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
}

.summary-item span {
  color: var(--color-text-muted);
  display: block;
  font-size: 12px;
  font-weight: 700;
}

.summary-item strong {
  color: var(--color-text);
  display: block;
  font-size: 24px;
  line-height: 1.1;
  margin-top: 6px;
}

.summary-item.danger {
  background: #fff7f6;
  border-color: #fecdca;
}

.summary-item.warning {
  background: #fffbeb;
  border-color: #fedf89;
}

.summary-item.default {
  background: #f8fafc;
}
</style>
