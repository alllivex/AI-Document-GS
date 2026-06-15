<template>
  <section class="entity-schema-config">
    <div class="toolbar">
      <div>
        <h3>数据结构</h3>
        <p>先按数据表查看整体结构，点击具体表后查看字段、主键和必填配置。</p>
      </div>
      <div class="actions">
        <el-button @click="importVisible = true">导入 Excel</el-button>
        <el-button type="primary" @click="exportSchema">导出 Excel</el-button>
      </div>
    </div>

    <el-form class="filters" @submit.prevent>
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索表名、字段名或中文名称"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button :loading="loadingTables || loadingFields" type="primary" @click="handleSearch">搜索</el-button>
    </el-form>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="schema-layout">
      <aside class="table-list">
        <div class="panel-title">
          <strong>数据表</strong>
          <span>{{ tables.length }} 张</span>
        </div>
        <el-table
          v-loading="loadingTables"
          :data="tables"
          border
          highlight-current-row
          row-key="table_name"
          @row-click="selectTable"
        >
          <el-table-column label="表" min-width="180">
            <template #default="{ row }">
              <div class="table-name">{{ row.table_name_cn || row.table_name }}</div>
              <div class="muted">{{ row.table_name }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="field_count" label="字段" width="72" />
        </el-table>
      </aside>

      <section class="field-panel">
        <div class="panel-title">
          <div>
            <strong>{{ selectedTableTitle }}</strong>
            <p v-if="selectedTable">
              主键：{{ selectedTable.primary_key_fields.join('、') || '-' }}，
              必填字段 {{ selectedTable.required_field_count }} 个
            </p>
          </div>
          <StatusTag v-if="selectedTable" type="processing" :label="`${total} 个字段`" />
        </div>

        <el-empty v-if="!selectedTable && !loadingTables" description="请选择左侧数据表查看字段" />
        <template v-else>
          <el-table v-loading="loadingFields" :data="fields" border>
            <el-table-column prop="field_name_cn" label="字段中文名" min-width="150" />
            <el-table-column prop="field_name" label="字段英文名" min-width="160" />
            <el-table-column prop="data_type" label="类型" width="120" />
            <el-table-column label="主键" width="90">
              <template #default="{ row }">
                <StatusTag :type="row.is_primary_key ? 'success' : 'default'" :label="row.is_primary_key ? '是' : '否'" />
              </template>
            </el-table-column>
            <el-table-column label="必填" width="90">
              <template #default="{ row }">
                <StatusTag :type="row.required ? 'warning' : 'default'" :label="row.required ? '是' : '否'" />
              </template>
            </el-table-column>
            <el-table-column prop="display_format" label="展示格式" min-width="120" />
            <el-table-column prop="description" label="说明" min-width="180" />
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
        </template>
      </section>
    </section>

    <EntitySchemaImportDialog
      v-model="importVisible"
      @imported="handleImported"
    />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import StatusTag from '../common/StatusTag.vue'
import EntitySchemaImportDialog from './EntitySchemaImportDialog.vue'
import { exportEntitySchemaUrl, listEntitySchema, listEntitySchemaTables } from '../../api/settings'
import type { EntitySchemaFieldRecord, EntitySchemaTableSummary } from '../../types/settings'

const tables = ref<EntitySchemaTableSummary[]>([])
const fields = ref<EntitySchemaFieldRecord[]>([])
const selectedTable = ref<EntitySchemaTableSummary | null>(null)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const loadingTables = ref(false)
const loadingFields = ref(false)
const importVisible = ref(false)
const errorMessage = ref('')

const selectedTableTitle = computed(() => {
  if (!selectedTable.value) {
    return '字段明细'
  }
  return selectedTable.value.table_name_cn || selectedTable.value.table_name
})

onMounted(loadTables)

async function loadTables() {
  loadingTables.value = true
  errorMessage.value = ''
  try {
    const response = await listEntitySchemaTables(keyword.value.trim() || undefined)
    tables.value = response.items
    if (!selectedTable.value || !tables.value.some((table) => table.table_name === selectedTable.value?.table_name)) {
      selectedTable.value = tables.value[0] || null
      page.value = 1
    }
    await loadFields()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '数据结构加载失败'
  } finally {
    loadingTables.value = false
  }
}

async function loadFields() {
  if (!selectedTable.value) {
    fields.value = []
    total.value = 0
    return
  }
  loadingFields.value = true
  errorMessage.value = ''
  try {
    const response = await listEntitySchema({
      table_name: selectedTable.value.table_name,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    fields.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '字段明细加载失败'
  } finally {
    loadingFields.value = false
  }
}

function selectTable(row: EntitySchemaTableSummary) {
  selectedTable.value = row
  page.value = 1
  loadFields()
}

function handleSearch() {
  page.value = 1
  loadTables()
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
  await loadTables()
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
  grid-template-columns: minmax(260px, 420px) auto;
  justify-content: start;
}

.schema-layout {
  align-items: start;
  display: grid;
  gap: 16px;
  grid-template-columns: 320px minmax(0, 1fr);
}

.table-list,
.field-panel {
  display: grid;
  gap: 12px;
  min-width: 0;
}

.panel-title {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
}

.panel-title strong {
  color: var(--color-text);
  font-size: 15px;
}

.panel-title span,
.panel-title p {
  color: var(--color-text-muted);
  font-size: 12px;
  margin: 4px 0 0;
}

.table-name {
  color: var(--color-text);
  font-weight: 700;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 4px;
}

@media (max-width: 1080px) {
  .schema-layout {
    grid-template-columns: 1fr;
  }
}
</style>
