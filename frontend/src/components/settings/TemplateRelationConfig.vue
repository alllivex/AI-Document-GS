<template>
  <section class="template-relation-config">
    <div class="toolbar">
      <div>
        <h3>模板关系</h3>
        <p>SQLite templates 和 template_tables 是运行时主数据源，Excel 仅用于导入和导出。</p>
      </div>
      <div class="actions">
        <el-button @click="importVisible = true">导入Excel</el-button>
        <el-button type="primary" @click="exportRelations">导出Excel</el-button>
      </div>
    </div>

    <el-form class="filters" @submit.prevent>
      <el-select v-model="templateId" clearable filterable placeholder="按模板筛选" @change="handleSearch" @clear="handleSearch">
        <el-option
          v-for="template in templates"
          :key="template.template_id"
          :label="`${template.template_name}（${template.template_file}）`"
          :value="template.template_id"
        />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索模板、文件或表名" @keyup.enter="loadRelations" @clear="loadRelations" />
      <el-button :loading="loading" type="primary" @click="handleSearch">搜索</el-button>
    </el-form>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <el-table v-loading="loading" :data="relations" border>
      <el-table-column prop="template_name" label="模板名称" min-width="180" />
      <el-table-column prop="template_file" label="模板文件" min-width="160" />
      <el-table-column prop="table_name_cn" label="表中文名" min-width="140" />
      <el-table-column prop="table_name" label="表英文名" min-width="150" />
      <el-table-column prop="role" label="角色" width="100" />
      <el-table-column prop="relation_type" label="关系类型" width="130" />
      <el-table-column prop="main_join_key" label="主表关联字段" min-width="140" />
      <el-table-column prop="table_join_key" label="当前表关联字段" min-width="140" />
      <el-table-column label="是否必需" width="100">
        <template #default="{ row }">
          <el-tag :type="row.required ? 'success' : 'info'">{{ row.required ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      background
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      @current-change="loadRelations"
      @size-change="handlePageSizeChange"
    />

    <TemplateRelationImportDialog v-model="importVisible" @imported="handleImported" />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TemplateRelationImportDialog from './TemplateRelationImportDialog.vue'
import { exportTemplateRelationsUrl, listTemplateFiles, listTemplateRelations } from '../../api/settings'
import type { TemplateFileRecord, TemplateRelationRecord } from '../../types/settings'

const relations = ref<TemplateRelationRecord[]>([])
const templates = ref<TemplateFileRecord[]>([])
const templateId = ref<number | undefined>()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const importVisible = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  await Promise.all([loadTemplates(), loadRelations()])
})

async function loadTemplates() {
  try {
    const response = await listTemplateFiles()
    templates.value = response.items
  } catch {
    templates.value = []
  }
}

async function loadRelations() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTemplateRelations({
      template_id: templateId.value,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    relations.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板关系列表加载失败'
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadRelations()
}

function handlePageSizeChange() {
  page.value = 1
  loadRelations()
}

function exportRelations() {
  window.open(exportTemplateRelationsUrl(), '_blank')
}

async function handleImported() {
  importVisible.value = false
  page.value = 1
  await Promise.all([loadTemplates(), loadRelations()])
}
</script>

<style scoped>
.template-relation-config {
  display: grid;
  gap: 16px;
}

.toolbar {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.toolbar h3 {
  margin: 0 0 6px;
}

.toolbar p {
  color: #606266;
  margin: 0;
}

.actions {
  display: flex;
  gap: 8px;
}

.filters {
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 360px) minmax(220px, 360px) auto;
  justify-content: start;
}
</style>
