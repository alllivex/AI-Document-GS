<template>
  <el-card class="template-card" shadow="never">
    <div class="card-top">
      <div class="template-icon">DOC</div>
      <StatusTag :status="template.is_active ? 'active' : 'inactive'" :label="template.is_active ? '启用' : '停用'" />
    </div>

    <h3>{{ template.template_name }}</h3>
    <p class="file-name">{{ template.template_file }}</p>

    <dl class="meta-list">
      <div>
        <dt>主表</dt>
        <dd>{{ mainTableText }}</dd>
      </div>
      <div>
        <dt>依赖表</dt>
        <dd>{{ template.required_table_count }} 必需 / {{ template.aux_table_count }} 辅表</dd>
      </div>
      <div>
        <dt>更新时间</dt>
        <dd>{{ formatTime(template.updated_at) }}</dd>
      </div>
    </dl>

    <div class="actions">
      <el-button @click="emit('view-detail', template.template_id)">查看详情</el-button>
      <el-button type="primary" @click="emit('use-template', template.template_id)">使用模板</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusTag from '../common/StatusTag.vue'
import type { TemplateListItem } from '../../types/template'

const props = defineProps<{
  template: TemplateListItem
}>()

const emit = defineEmits<{
  'view-detail': [templateId: number]
  'use-template': [templateId: number]
}>()

const mainTableText = computed(() => {
  return props.template.main_table_cn
    ? `${props.template.main_table_cn}（${props.template.main_table}）`
    : props.template.main_table
})

function formatTime(value: string) {
  return value ? new Date(value).toLocaleDateString() : '-'
}
</script>

<style scoped>
.template-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  min-width: 0;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.template-card:hover {
  border-color: #bfd0f8;
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.template-card :deep(.el-card__body) {
  display: grid;
  gap: 14px;
  padding: 18px;
}

.card-top {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.template-icon {
  align-items: center;
  background: var(--color-primary-soft);
  border: 1px solid #d9e5ff;
  border-radius: 8px;
  color: var(--color-primary);
  display: flex;
  font-size: 11px;
  font-weight: 800;
  height: 34px;
  justify-content: center;
  width: 42px;
}

.template-card h3 {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 750;
  line-height: 1.4;
  margin: 0;
}

.file-name {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: -6px 0 0;
  overflow-wrap: anywhere;
}

.meta-list {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  display: grid;
  gap: 0;
  margin: 0;
  overflow: hidden;
}

.meta-list div {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
}

.meta-list div + div {
  border-top: 1px solid var(--color-border);
}

.meta-list dt {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.meta-list dd {
  color: var(--color-text);
  font-weight: 650;
  margin: 0;
  overflow-wrap: anywhere;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
</style>
