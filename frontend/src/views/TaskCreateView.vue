<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2>新建生成任务</h2>
        <p>选择模板后创建任务，再按依赖表上传 Excel。</p>
      </div>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="section">
      <h3>1. 选择模板</h3>
      <el-form label-width="100px">
        <el-form-item label="模板">
          <TemplateSelector
            v-model="selectedTemplateId"
            :disabled="Boolean(task)"
            @requirements-loaded="onRequirementsLoaded"
          />
        </el-form-item>
        <el-form-item label="任务名称">
          <el-input v-model="taskName" :disabled="Boolean(task)" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="启用 AI">
          <el-switch v-model="aiEnabled" :disabled="Boolean(task)" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canCreateTask" :loading="creating" @click="handleCreateTask">
            创建任务
          </el-button>
        </el-form-item>
      </el-form>
    </section>

    <section v-if="task" class="section">
      <h3>2. 上传 Excel</h3>
      <el-alert
        :title="`任务已创建：${task.task_id}`"
        type="success"
        show-icon
        :closable="false"
      />
      <RequiredTableUploadList
        :task-id="task.task_id"
        :tables="requiredTables"
        @uploaded="onUploaded"
      />
    </section>

    <section v-if="task" class="section">
      <div class="section-title">
        <h3>3. 校验数据</h3>
        <el-button type="primary" :loading="validating" @click="handleValidate">开始校验</el-button>
      </div>
      <ValidationReportPanel :report="validationReport" :loading="validating" />
    </section>

    <section v-if="task" class="section">
      <div class="section-title">
        <h3>4. 生成文档</h3>
        <el-button type="primary" :loading="generating" @click="handleGenerate">开始生成</el-button>
      </div>

      <el-alert
        v-if="generationResult"
        :title="generationTitle"
        :type="generationResult.status === 'failed' ? 'error' : 'success'"
        show-icon
        :closable="false"
      />

      <OutputDocumentList
        :task-id="task.task_id"
        :documents="documents"
        :loading="loadingOutputs"
      />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import RequiredTableUploadList from '../components/RequiredTableUploadList.vue'
import OutputDocumentList from '../components/OutputDocumentList.vue'
import TemplateSelector from '../components/TemplateSelector.vue'
import ValidationReportPanel from '../components/ValidationReportPanel.vue'
import { createTask, generateTask, listTaskOutputs, validateTask } from '../api/tasks'
import type {
  CreateTaskResponse,
  DocumentRecord,
  GenerateTaskResponse,
  UploadedFileResponse,
} from '../types/task'
import type { RequiredTable, TemplateRequirements } from '../types/template'
import type { ValidateTaskResponse } from '../types/validation'

const route = useRoute()

const initialTemplateId = Number(route.query.template_id)
const selectedTemplateId = ref<number | null>(Number.isInteger(initialTemplateId) && initialTemplateId > 0 ? initialTemplateId : null)
const taskName = ref('')
const aiEnabled = ref(true)
const requirements = ref<TemplateRequirements | null>(null)
const task = ref<CreateTaskResponse | null>(null)
const validationReport = ref<ValidateTaskResponse | null>(null)
const generationResult = ref<GenerateTaskResponse | null>(null)
const documents = ref<DocumentRecord[]>([])
const creating = ref(false)
const validating = ref(false)
const generating = ref(false)
const loadingOutputs = ref(false)
const errorMessage = ref('')

const requiredTables = computed<RequiredTable[]>(() => {
  return task.value?.required_tables.length ? task.value.required_tables : requirements.value?.required_tables || []
})

const canCreateTask = computed(() => {
  return Boolean(selectedTemplateId.value && taskName.value.trim() && !task.value)
})

const generationTitle = computed(() => {
  if (!generationResult.value) {
    return ''
  }
  const result = generationResult.value
  return `生成完成：总数 ${result.total_rows}，成功 ${result.success_count}，失败 ${result.failed_count}`
})

function onRequirementsLoaded(value: TemplateRequirements | null) {
  requirements.value = value
  if (value && !taskName.value) {
    taskName.value = `${value.template_name}_${new Date().toLocaleString()}`
    aiEnabled.value = true
  }
}

async function handleCreateTask() {
  if (!selectedTemplateId.value) {
    return
  }
  creating.value = true
  errorMessage.value = ''
  try {
    task.value = await createTask({
      task_name: taskName.value.trim(),
      template_id: selectedTemplateId.value,
      ai_enabled: aiEnabled.value,
    })
    ElMessage.success('任务创建成功')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务创建失败'
  } finally {
    creating.value = false
  }
}

function onUploaded(value: UploadedFileResponse) {
  ElMessage.success(`${value.table_name} 已上传`)
}

async function handleValidate() {
  if (!task.value) {
    return
  }
  validating.value = true
  errorMessage.value = ''
  try {
    validationReport.value = await validateTask(task.value.task_id)
    ElMessage.success('校验完成')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '校验失败'
  } finally {
    validating.value = false
  }
}

async function handleGenerate() {
  if (!task.value) {
    return
  }
  generating.value = true
  errorMessage.value = ''
  try {
    generationResult.value = await generateTask(task.value.task_id)
    await refreshOutputs()
    ElMessage.success('生成流程已结束')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    generating.value = false
  }
}

async function refreshOutputs() {
  if (!task.value) {
    return
  }
  loadingOutputs.value = true
  try {
    const response = await listTaskOutputs(task.value.task_id)
    documents.value = response.items
  } finally {
    loadingOutputs.value = false
  }
}
</script>

<style scoped>
.page {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.page-header h2,
.section h3 {
  margin: 0 0 8px;
}

.page-header p {
  color: #606266;
  margin: 0;
}

.section {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  display: grid;
  gap: 12px;
  padding: 16px;
}

.section-title {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
</style>
