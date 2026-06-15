<template>
  <div class="upload-list">
    <el-table :data="tables" border>
      <el-table-column label="表名" min-width="220">
        <template #default="{ row }">
          <div>{{ tableLabel(row) }}</div>
          <div class="muted">{{ row.table_name }}</div>
        </template>
      </el-table-column>
      <el-table-column label="关系" width="140">
        <template #default="{ row }">
          <StatusTag :type="row.role === 'main' ? 'success' : 'default'" :label="row.role === 'main' ? '主表' : '辅表'" />
        </template>
      </el-table-column>
      <el-table-column label="关联键" min-width="180">
        <template #default="{ row }">
          <span v-if="row.relation_type === 'main'">-</span>
          <span v-else>{{ row.main_join_key }} → {{ row.table_join_key }}</span>
        </template>
      </el-table-column>
      <el-table-column label="上传 Excel" min-width="260">
        <template #default="{ row }">
          <label class="file-picker" :class="{ disabled: !taskId || uploading[row.table_name] }">
            <span>{{ uploaded[row.table_name] ? '重新上传' : '选择文件' }}</span>
            <input
              :disabled="!taskId || uploading[row.table_name]"
              accept=".xlsx"
              type="file"
              @change="onFileChange(row.table_name, $event)"
            />
          </label>
          <div v-if="uploaded[row.table_name]" class="uploaded">
            <strong>{{ uploaded[row.table_name].original_filename }}</strong>
            <span>{{ uploaded[row.table_name].row_count }} 行 / {{ uploaded[row.table_name].column_count }} 列</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <StatusTag v-if="uploaded[row.table_name]" type="success" label="完成" />
          <StatusTag v-else-if="uploading[row.table_name]" type="processing" label="上传中" />
          <StatusTag v-else type="default" label="待上传" />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import StatusTag from './common/StatusTag.vue'
import { uploadTaskFile } from '../api/tasks'
import type { UploadedFileResponse } from '../types/task'
import type { RequiredTable } from '../types/template'

const props = defineProps<{
  taskId: string
  tables: RequiredTable[]
}>()

const emit = defineEmits<{
  uploaded: [value: UploadedFileResponse]
}>()

const uploaded = reactive<Record<string, UploadedFileResponse>>({})
const uploading = reactive<Record<string, boolean>>({})

async function onFileChange(tableName: string, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) {
    return
  }
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    ElMessage.error('只能上传 .xlsx 文件')
    input.value = ''
    return
  }
  if (uploaded[tableName]) {
    try {
      await ElMessageBox.confirm(
        '重新上传会覆盖该表已上传文件，并影响后续校验和生成结果，是否继续？',
        '确认重新上传',
        {
          type: 'warning',
          confirmButtonText: '继续上传',
          cancelButtonText: '取消',
        },
      )
    } catch {
      input.value = ''
      return
    }
  }

  uploading[tableName] = true
  try {
    const result = await uploadTaskFile(props.taskId, tableName, file)
    uploaded[tableName] = result
    emit('uploaded', result)
    ElMessage.success(`${tableName} 上传完成`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '上传失败')
  } finally {
    uploading[tableName] = false
    input.value = ''
  }
}

function tableLabel(row: RequiredTable) {
  return row.table_name_cn || row.table_name
}
</script>

<style scoped>
.upload-list {
  width: 100%;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
  margin-top: 4px;
}

.file-picker {
  align-items: center;
  background: #fff;
  border: 1px solid var(--color-border-strong);
  border-radius: 6px;
  color: var(--color-primary);
  cursor: pointer;
  display: inline-flex;
  font-size: 13px;
  font-weight: 700;
  height: 32px;
  padding: 0 12px;
}

.file-picker:hover {
  background: var(--color-primary-soft);
  border-color: #aac2ff;
}

.file-picker.disabled {
  color: var(--color-text-muted);
  cursor: not-allowed;
  opacity: 0.65;
}

.file-picker input {
  display: none;
}

.uploaded {
  color: var(--color-text-muted);
  display: grid;
  font-size: 12px;
  gap: 2px;
  margin-top: 8px;
}

.uploaded strong {
  color: var(--color-text);
  font-weight: 650;
  overflow-wrap: anywhere;
}
</style>
