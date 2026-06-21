<template>
  <el-dialog :model-value="modelValue" title="模板详情" width="820px" @update:model-value="emit('update:modelValue', $event)">
    <div v-loading="loading" class="dialog-body">
      <el-empty v-if="!loading && !detail" description="暂无模板详情" />

      <template v-if="detail">
        <section class="detail-summary">
          <div>
            <span>模板状态</span>
            <strong>{{ detail.is_active ? '启用' : '停用' }}</strong>
          </div>
          <div>
            <span>主表</span>
            <strong>{{ tableText(detail.main_table) }}</strong>
          </div>
          <div>
            <span>辅表数量</span>
            <strong>{{ detail.aux_tables.length }}</strong>
          </div>
        </section>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="模板名称">{{ detail.template_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.is_active ? '启用' : '停用' }}</el-descriptions-item>
          <el-descriptions-item label="模板文件">{{ detail.template_file }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ detail.template_file_type === 'xlsx' ? 'Excel' : 'Word' }}</el-descriptions-item>
          <el-descriptions-item label="模板路径">{{ detail.template_path }}</el-descriptions-item>
          <el-descriptions-item label="主表" :span="2">{{ tableText(detail.main_table) }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="tableRows" border>
          <el-table-column label="表名" min-width="180">
            <template #default="{ row }">{{ tableText(row) }}</template>
          </el-table-column>
          <el-table-column prop="relation_type" label="关系类型" width="140" />
          <el-table-column label="是否必需" width="110">
            <template #default="{ row }">
              <StatusTag :type="row.required ? 'success' : 'default'" :label="row.required ? '必需' : '可选'" />
            </template>
          </el-table-column>
          <el-table-column prop="main_join_key" label="主表关联字段" min-width="140" />
          <el-table-column prop="table_join_key" label="本表关联字段" min-width="140" />
        </el-table>
      </template>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
      <el-button v-if="detail" type="primary" @click="emit('use-template', detail.template_id)">使用此模板生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from '../common/StatusTag.vue'
import type { TemplateDetail, TemplateTableSummary } from '../../types/template'

const props = defineProps<{
  modelValue: boolean
  detail: TemplateDetail | null
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'use-template': [templateId: number]
}>()

const tableRows = computed<TemplateTableSummary[]>(() => {
  return props.detail ? [props.detail.main_table, ...props.detail.aux_tables] : []
})

function tableText(table: TemplateTableSummary) {
  return table.table_name_cn ? `${table.table_name_cn}（${table.table_name}）` : table.table_name
}
</script>

<style scoped>
.dialog-body {
  display: grid;
  gap: 16px;
  min-height: 160px;
}

.detail-summary {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-summary div {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
}

.detail-summary span {
  color: var(--color-text-muted);
  display: block;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
}

.detail-summary strong {
  color: var(--color-text);
  display: block;
  font-size: 15px;
  overflow-wrap: anywhere;
}
</style>
