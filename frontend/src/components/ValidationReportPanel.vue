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
        <el-table-column label="问题类型" width="180">
          <template #default="{ row }">{{ codeText(row.code) }}</template>
        </el-table-column>
        <el-table-column label="影响对象" min-width="190">
          <template #default="{ row }">
            {{ [row.table_name, row.field_name].filter(Boolean).join('.') || row.template_file || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="问题描述" min-width="260" />
        <el-table-column label="修复建议" min-width="260">
          <template #default="{ row }">
            {{ row.suggestion || '请根据问题描述检查模板、实体 Schema 或上传的 Excel 数据。' }}
          </template>
        </el-table-column>
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

function codeText(code: string) {
  const map: Record<string, string> = {
    template_file_missing: '模板文件缺失',
    missing_required_table: '必需表缺失',
    missing_optional_table: '可选表缺失',
    missing_required_field: '必填字段缺失',
    missing_primary_key_field: '主键字段缺失',
    empty_primary_key: '主键为空',
    duplicated_primary_key: '主键重复',
    missing_aux_join_key: '关联键缺失',
    one_to_one_multiple_rows: '一对一关系重复',
    missing_field: '模板变量异常',
  }
  return map[code] || code
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
