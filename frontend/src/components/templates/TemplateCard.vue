<template>
  <el-card class="template-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <h3>{{ template.template_name }}</h3>
        <el-tag :type="template.is_active ? 'success' : 'info'">
          {{ template.is_active ? '启用' : '停用' }}
        </el-tag>
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
      <el-button type="primary" @click="emit('use-template', template.template_id)">使用此模板生成</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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
  min-width: 0;
}

.card-header {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.card-header h3 {
  font-size: 16px;
  line-height: 1.4;
  margin: 0;
}

.meta-list {
  display: grid;
  gap: 10px;
  margin: 0;
}

.meta-list div {
  display: grid;
  gap: 4px;
}

.meta-list dt {
  color: #909399;
  font-size: 12px;
}

.meta-list dd {
  color: #303133;
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
