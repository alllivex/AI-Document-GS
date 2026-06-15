<template>
  <el-card class="template-card" shadow="never">
    <template #header>
      <div class="card-header">
        <h3>{{ template.template_name }}</h3>
        <StatusTag :status="template.is_active ? 'active' : 'inactive'" :label="template.is_active ? '启用' : '停用'" />
      </div>
    </template>

    <dl class="meta-list">
      <div>
        <dt>主表</dt>
        <dd>{{ mainTableText }}</dd>
      </div>
      <div>
        <dt>辅表数量</dt>
        <dd>{{ template.aux_table_count }}</dd>
      </div>
      <div>
        <dt>必需表数量</dt>
        <dd>{{ template.required_table_count }}</dd>
      </div>
      <div>
        <dt>模板文件</dt>
        <dd>{{ template.template_file }}</dd>
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
</script>

<style scoped>
.template-card {
  border: 1px solid #edf0f5;
  border-radius: 14px;
  box-shadow: 0 6px 18px rgba(16, 24, 40, 0.05);
  min-width: 0;
  transition:
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.template-card:hover {
  box-shadow: 0 12px 28px rgba(16, 24, 40, 0.09);
  transform: translateY(-2px);
}

.template-card :deep(.el-card__header) {
  border-bottom-color: #edf0f5;
  padding: 18px 18px 14px;
}

.template-card :deep(.el-card__body) {
  padding: 18px;
}

.card-header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.card-header h3 {
  color: #1f2937;
  font-size: 18px;
  font-weight: 650;
  line-height: 1.4;
  margin: 0;
}

.meta-list {
  display: grid;
  gap: 12px;
  margin: 0;
}

.meta-list div {
  display: grid;
  gap: 4px;
}

.meta-list dt {
  color: #667085;
  font-size: 12px;
  font-weight: 600;
}

.meta-list dd {
  color: #344054;
  margin: 0;
  overflow-wrap: anywhere;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
