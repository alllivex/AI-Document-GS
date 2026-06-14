<template>
  <div class="template-selector">
    <el-select
      :model-value="modelValue"
      :disabled="disabled"
      :loading="loading"
      clearable
      filterable
      placeholder="请选择模板"
      style="width: 100%"
      @update:model-value="handleSelect"
    >
      <el-option
        v-for="template in templates"
        :key="template.template_id"
        :label="template.template_name"
        :value="template.template_id"
      >
        <span>{{ template.template_name }}</span>
        <span class="template-file">{{ template.template_file }}</span>
      </el-option>
    </el-select>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <div v-if="requirements" class="template-meta">
      <div>主表：{{ displayTable(requirements.main_table) }}</div>
      <div>主键：{{ requirements.primary_key_field }}</div>
      <div>依赖表：{{ requirements.required_tables.length }} 张</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getTemplateRequirements, listTemplates } from '../api/templates'
import type { TemplateListItem, TemplateRequirements } from '../types/template'

const props = defineProps<{
  modelValue: number | null
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
  'requirements-loaded': [value: TemplateRequirements | null]
}>()

const templates = ref<TemplateListItem[]>([])
const requirements = ref<TemplateRequirements | null>(null)
const loading = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  await loadTemplates()
  if (props.modelValue) {
    await loadRequirements(props.modelValue)
  }
})

async function loadTemplates() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTemplates()
    templates.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板列表加载失败'
  } finally {
    loading.value = false
  }
}

async function handleSelect(value: number | null) {
  emit('update:modelValue', value)
  await loadRequirements(value)
}

async function loadRequirements(templateId: number | null) {
  requirements.value = null
  emit('requirements-loaded', null)
  if (!templateId) {
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    requirements.value = await getTemplateRequirements(templateId)
    emit('requirements-loaded', requirements.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板依赖加载失败'
  } finally {
    loading.value = false
  }
}

function displayTable(tableName: string) {
  const table = requirements.value?.required_tables.find((item) => item.table_name === tableName)
  return table?.table_name_cn ? `${table.table_name_cn}（${tableName}）` : tableName
}
</script>

<style scoped>
.template-selector {
  display: grid;
  gap: 12px;
}

.template-file {
  color: #909399;
  float: right;
  font-size: 12px;
}

.template-meta {
  color: #606266;
  display: flex;
  flex-wrap: wrap;
  font-size: 13px;
  gap: 12px;
}
</style>
