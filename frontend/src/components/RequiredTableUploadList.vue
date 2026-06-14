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
          <el-tag :type="row.role === 'main' ? 'success' : 'info'">
            {{ row.role === 'main' ? '主表' : '辅表' }}
          </el-tag>
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
          <input
            :disabled="!taskId || uploading[row.table_name]"
            accept=".xlsx"
            type="file"
            @change="onFileChange(row.table_name, $event)"
          />
          <div v-if="uploaded[row.table_name]" class="uploaded">
            已上传：{{ uploaded[row.table_name].original_filename }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="uploaded[row.table_name]" type="success">完成</el-tag>
          <el-tag v-else-if="uploading[row.table_name]" type="warning">上传中</el-tag>
          <el-tag v-else type="info">待上传</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
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

.muted,
.uploaded {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
