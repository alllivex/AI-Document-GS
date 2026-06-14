<template>
  <el-dialog :model-value="modelValue" title="导入模板关系" width="760px" @update:model-value="handleVisibleChange">
    <div class="import-dialog">
      <el-upload
        accept=".xlsx"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
      >
        <el-button>选择 template_relation.xlsx</el-button>
        <template #tip>
          <div class="upload-tip">导入分为预校验和确认导入两步，预校验不会写入数据库。</div>
        </template>
      </el-upload>

      <el-button type="primary" :loading="previewing" :disabled="!selectedFile" @click="previewImport">
        预校验
      </el-button>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

      <template v-if="preview">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="总行数">{{ preview.summary.total_rows }}</el-descriptions-item>
          <el-descriptions-item label="新增">{{ preview.summary.create_count }}</el-descriptions-item>
          <el-descriptions-item label="更新">{{ preview.summary.update_count }}</el-descriptions-item>
          <el-descriptions-item label="错误">{{ preview.summary.error_count }}</el-descriptions-item>
          <el-descriptions-item label="警告">{{ preview.summary.warning_count }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="preview.items" border max-height="280">
          <el-table-column prop="row_number" label="行号" width="90" />
          <el-table-column prop="action" label="动作" width="100" />
          <el-table-column label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="levelType(row.level)">{{ levelText(row.level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="信息" min-width="320" />
        </el-table>
      </template>
    </div>

    <template #footer>
      <el-button @click="handleVisibleChange(false)">取消</el-button>
      <el-button type="primary" :loading="committing" :disabled="!preview?.can_commit" @click="commitImport">
        确认导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { commitTemplateRelationImport, previewTemplateRelationImport } from '../../api/settings'
import type { TemplateRelationImportLevel, TemplateRelationImportPreview } from '../../types/settings'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  imported: []
}>()

const selectedFile = ref<File | null>(null)
const preview = ref<TemplateRelationImportPreview | null>(null)
const previewing = ref(false)
const committing = ref(false)
const errorMessage = ref('')

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      resetState()
    }
  },
)

function handleVisibleChange(value: boolean) {
  emit('update:modelValue', value)
}

function handleFileChange(uploadFile: UploadFile) {
  errorMessage.value = ''
  preview.value = null
  const rawFile = uploadFile.raw
  if (!rawFile) {
    selectedFile.value = null
    return
  }
  if (!rawFile.name.toLowerCase().endsWith('.xlsx')) {
    selectedFile.value = null
    errorMessage.value = '仅支持上传 .xlsx 文件'
    return
  }
  selectedFile.value = rawFile
}

function handleFileRemove() {
  selectedFile.value = null
  preview.value = null
}

async function previewImport() {
  if (!selectedFile.value) {
    return
  }
  previewing.value = true
  errorMessage.value = ''
  try {
    preview.value = await previewTemplateRelationImport(selectedFile.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板关系预校验失败'
  } finally {
    previewing.value = false
  }
}

async function commitImport() {
  if (!preview.value?.can_commit) {
    return
  }
  committing.value = true
  errorMessage.value = ''
  try {
    await commitTemplateRelationImport(preview.value.import_id)
    ElMessage.success('模板关系导入成功')
    emit('imported')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板关系导入失败'
  } finally {
    committing.value = false
  }
}

function levelType(level: TemplateRelationImportLevel) {
  if (level === 'error') {
    return 'danger'
  }
  if (level === 'warning') {
    return 'warning'
  }
  return 'success'
}

function levelText(level: TemplateRelationImportLevel) {
  const map: Record<TemplateRelationImportLevel, string> = {
    info: '信息',
    warning: '警告',
    error: '错误',
  }
  return map[level]
}

function resetState() {
  selectedFile.value = null
  preview.value = null
  previewing.value = false
  committing.value = false
  errorMessage.value = ''
}
</script>

<style scoped>
.import-dialog {
  display: grid;
  gap: 16px;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
</style>
