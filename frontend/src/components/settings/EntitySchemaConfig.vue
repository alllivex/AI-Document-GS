<template>
  <section class="entity-schema-config">
    <div class="toolbar">
      <div>
        <h3>实体Schema</h3>
        <p>SQLite fields 表是运行时主数据源，Excel 仅用于导入和导出。</p>
      </div>
      <div class="actions">
        <el-button @click="importVisible = true">导入Excel</el-button>
        <el-button type="primary" @click="exportSchema">导出Excel</el-button>
      </div>
    </div>

    <el-form class="filters" @submit.prevent>
      <el-input v-model="tableName" clearable placeholder="按表英文名筛选" @keyup.enter="loadFields" @clear="loadFields" />
      <el-input v-model="keyword" clearable placeholder="搜索中文或英文表字段" @keyup.enter="loadFields" @clear="loadFields" />
      <el-button :loading="loading" type="primary" @click="handleSearch">搜索</el-button>
    </el-form>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <el-table v-loading="loading" :data="fields" border>
      <el-table-column prop="table_name_cn" label="表中文名" min-width="150" />
      <el-table-column prop="table_name" label="表英文名" min-width="160" />
      <el-table-column prop="field_name_cn" label="字段中文名" min-width="150" />
      <el-table-column prop="field_name" label="字段英文名" min-width="160" />
      <el-table-column prop="data_type" label="类型" width="120" />
      <el-table-column label="主键" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_primary_key ? 'success' : 'info'">{{ row.is_primary_key ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="必填" width="90">
        <template #default="{ row }">
          <el-tag :type="row.required ? 'warning' : 'info'">{{ row.required ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="display_format" label="展示格式" min-width="120" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      background
      layout="total, sizes, prev, pager, next"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      @current-change="loadFields"
      @size-change="handlePageSizeChange"
    />

    <EntitySchemaImportDialog
      v-model="importVisible"
      @imported="handleImported"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EntitySchemaImportDialog from './EntitySchemaImportDialog.vue'
import { exportEntitySchemaUrl, listEntitySchema } from '../../api/settings'
import type { EntitySchemaFieldRecord } from '../../types/settings'

const fields = ref<EntitySchemaFieldRecord[]>([])
const tableName = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loading = ref(false)
const importVisible = ref(false)
const errorMessage = ref('')

onMounted(loadFields)

async function loadFields() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listEntitySchema({
      table_name: tableName.value.trim() || undefined,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    fields.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '实体Schema加载失败'
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadFields()
}

function handlePageSizeChange() {
  page.value = 1
  loadFields()
}

function exportSchema() {
  window.open(exportEntitySchemaUrl(), '_blank')
}

async function handleImported() {
  importVisible.value = false
  page.value = 1
  await loadFields()
}
</script>

<style scoped>
.entity-schema-config {
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
  grid-template-columns: minmax(180px, 260px) minmax(220px, 360px) auto;
  justify-content: start;
}
</style>
