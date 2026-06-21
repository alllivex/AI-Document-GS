<template>
  <section class="template-file-manager">
    <div class="toolbar">
      <div>
        <h3>模板文件</h3>
        <p>管理用于生成任务的 Word 和 Excel 模板文件；模板关系配置在后续模块维护。</p>
      </div>
      <el-button type="primary" @click="uploadVisible = true">上传新模板</el-button>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <el-table v-loading="loading" :data="templateFiles" border>
      <el-table-column prop="template_name" label="模板名称" min-width="180" />
      <el-table-column prop="original_filename" label="原始文件名" min-width="200" />
      <el-table-column prop="template_file" label="系统文件名" min-width="160" />
      <el-table-column label="类型" width="90">
        <template #default="{ row }">{{ row.template_file_type === 'xlsx' ? 'Excel' : 'Word' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <StatusTag :type="row.is_active ? 'success' : 'default'" :label="row.is_active ? '启用' : '停用'" />
        </template>
      </el-table-column>
      <el-table-column label="上传时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="downloadTemplate(row.template_id)">下载</el-button>
          <el-button link type="primary" @click="openReplaceDialog(row)">更换</el-button>
          <el-button
            v-if="row.is_active"
            link
            type="danger"
            @click="confirmDeactivate(row)"
          >
            停用
          </el-button>
          <el-button
            v-else
            link
            type="success"
            @click="confirmActivate(row)"
          >
            启用
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <TemplateUploadDialog
      v-model="uploadVisible"
      @uploaded="handleUploaded"
    />
    <TemplateReplaceDialog
      v-model="replaceVisible"
      :template="replaceTarget"
      @replaced="handleReplaced"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import StatusTag from '../common/StatusTag.vue'
import TemplateReplaceDialog from './TemplateReplaceDialog.vue'
import TemplateUploadDialog from './TemplateUploadDialog.vue'
import {
  activateTemplateFile,
  deactivateTemplateFile,
  downloadTemplateFileUrl,
  listTemplateFiles,
} from '../../api/settings'
import type { TemplateFileRecord } from '../../types/settings'

const templateFiles = ref<TemplateFileRecord[]>([])
const loading = ref(false)
const uploadVisible = ref(false)
const replaceVisible = ref(false)
const replaceTarget = ref<TemplateFileRecord | null>(null)
const errorMessage = ref('')

onMounted(loadTemplateFiles)

async function loadTemplateFiles() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTemplateFiles()
    templateFiles.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板文件列表加载失败'
  } finally {
    loading.value = false
  }
}

function downloadTemplate(templateId: number) {
  window.open(downloadTemplateFileUrl(templateId), '_blank')
}

function openReplaceDialog(template: TemplateFileRecord) {
  replaceTarget.value = template
  replaceVisible.value = true
}

async function confirmDeactivate(template: TemplateFileRecord) {
  try {
    await ElMessageBox.confirm(
      `确认停用模板“${template.template_name}”？停用后不会从磁盘删除文件。`,
      '停用模板',
      {
        confirmButtonText: '确认停用',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  try {
    await deactivateTemplateFile(template.template_id)
    ElMessage.success('模板已停用')
    await loadTemplateFiles()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板停用失败'
  }
}

async function confirmActivate(template: TemplateFileRecord) {
  try {
    await ElMessageBox.confirm(
      `确认启用模板“${template.template_name}”？启用后可用于新建生成任务。`,
      '启用模板',
      {
        confirmButtonText: '确认启用',
        cancelButtonText: '取消',
        type: 'success',
      },
    )
  } catch {
    return
  }

  try {
    await activateTemplateFile(template.template_id)
    ElMessage.success('模板已启用')
    await loadTemplateFiles()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板启用失败'
  }
}

async function handleUploaded() {
  uploadVisible.value = false
  ElMessage.success('模板上传成功')
  await loadTemplateFiles()
}

async function handleReplaced() {
  replaceVisible.value = false
  replaceTarget.value = null
  ElMessage.success('模板更换成功')
  await loadTemplateFiles()
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : '-'
}
</script>

<style scoped>
.template-file-manager {
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
</style>
