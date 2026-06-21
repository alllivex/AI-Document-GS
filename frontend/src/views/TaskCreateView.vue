<template>
  <main class="page">
    <div class="page-header">
      <div>
        <div class="page-kicker">Generation Flow</div>
        <h2 class="page-title">新建生成任务</h2>
        <p class="page-desc">按模板选择、Excel 上传、生成前校验、文档生成四步完成批量输出。</p>
      </div>
      <div class="actions" v-if="task">
        <el-button @click="refreshOutputs">刷新输出</el-button>
      </div>
    </div>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="page-card flow-card">
      <el-steps :active="activeStep" finish-status="success" align-center>
        <el-step title="选择模板" :description="task ? task.template_name : '创建任务'" />
        <el-step title="上传 Excel" :description="uploadProgressText" />
        <el-step title="校验数据" :description="validationStepText" />
        <el-step title="生成文档" :description="generationStepText" />
      </el-steps>
    </section>

    <section class="create-layout">
      <div class="main-flow">
        <section class="page-card section" :class="{ locked: Boolean(task) }">
          <div class="section-title">
            <div>
              <h3>1. 选择模板并创建任务</h3>
              <p>选择业务模板后，系统会自动带出所需 Excel 表。</p>
            </div>
            <StatusTag :type="task ? 'success' : 'processing'" :label="task ? '已创建' : '待创建'" />
          </div>

          <el-form label-width="96px" class="task-form">
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
            <el-form-item label="AI 生成">
              <div class="switch-row">
                <el-switch v-model="aiEnabled" :disabled="Boolean(task) || isXlsxTemplate" />
                <span v-if="isXlsxTemplate">Excel 模板首版不支持 AI 生成。</span>
                <span v-else>启用后会替换模板中的 AI 段落，输出仍为干净 Word。</span>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canCreateTask" :loading="creating" @click="handleCreateTask">
                创建任务
              </el-button>
            </el-form-item>
          </el-form>
        </section>

        <section class="page-card section" :class="{ disabled: !task }">
          <div class="section-title">
            <div>
              <h3>2. 上传 Excel 数据</h3>
              <p>业务数据统一上传到任务数据目录，用于后续校验、生成和溯源。</p>
            </div>
            <StatusTag :type="allRequiredUploaded ? 'success' : task ? 'processing' : 'default'" :label="uploadStatusText" />
          </div>

          <el-alert
            v-if="task"
            :title="`任务已创建：${task.task_id}`"
            type="success"
            show-icon
            :closable="false"
          />
          <el-empty v-else description="请先创建任务，再上传 Excel" />
          <RequiredTableUploadList
            v-if="task"
            :task-id="task.task_id"
            :tables="requiredTables"
            @uploaded="onUploaded"
          />
        </section>

        <section class="page-card section" :class="{ disabled: !task }">
          <div class="section-title">
            <div>
              <h3>3. 生成前校验</h3>
              <p>检查模板变量、必填字段、主键、Excel 字段及当前模板类型支持的能力。</p>
            </div>
            <el-button type="primary" :disabled="!task || !allRequiredUploaded" :loading="validating" @click="handleValidate">
              开始校验
            </el-button>
          </div>
          <ValidationReportPanel :report="validationReport" :loading="validating" />
        </section>

        <section class="page-card section" :class="{ disabled: !task }">
          <div class="section-title">
            <div>
              <h3>4. 生成文档</h3>
              <p>按主表行批量生成 Word 或 Excel、预览 JSON 和溯源 JSON。</p>
            </div>
            <el-button type="primary" :disabled="!canGenerate" :loading="generating" @click="handleGenerate">
              开始生成
            </el-button>
          </div>

          <div v-if="generating || generationProgress" class="generation-progress">
            <div class="progress-heading">
              <strong>{{ generationProgressText }}</strong>
              <span>{{ generationPercent }}%</span>
            </div>
            <el-progress :percentage="generationPercent" :status="generationProgressStatus" />
          </div>

          <el-alert
            v-if="generationResult"
            :title="generationTitle"
            :type="generationResult.status === 'failed' ? 'error' : 'success'"
            show-icon
            :closable="false"
          />

          <OutputDocumentList
            v-if="task"
            :task-id="task.task_id"
            :documents="documents"
            :loading="loadingOutputs"
          />
          <el-empty v-else description="完成前序步骤后，这里会显示输出文档" />
        </section>
      </div>

      <aside class="page-card side-summary">
        <h3>任务摘要</h3>
        <dl>
          <div>
            <dt>模板</dt>
            <dd>{{ requirements?.template_name || task?.template_name || '未选择' }}</dd>
          </div>
          <div>
            <dt>所需表</dt>
            <dd>{{ requiredTables.length }} 张，已上传 {{ uploadedCount }} 张</dd>
          </div>
          <div>
            <dt>AI 生成</dt>
            <dd>{{ aiEnabled ? '启用' : '关闭' }}</dd>
          </div>
          <div>
            <dt>输出文档</dt>
            <dd>{{ documents.length }} 份</dd>
          </div>
        </dl>
        <div class="info-strip">
          <strong>流程提示</strong>
          <span>校验通过后再生成文档，可以更早发现字段缺失和模板变量问题。</span>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import RequiredTableUploadList from '../components/RequiredTableUploadList.vue'
import OutputDocumentList from '../components/OutputDocumentList.vue'
import TemplateSelector from '../components/TemplateSelector.vue'
import ValidationReportPanel from '../components/ValidationReportPanel.vue'
import StatusTag from '../components/common/StatusTag.vue'
import { createTask, generateTask, getTask, listTaskOutputs, validateTask } from '../api/tasks'
import type {
  CreateTaskResponse,
  DocumentRecord,
  GenerateTaskResponse,
  TaskProgressResponse,
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
const generationProgress = ref<TaskProgressResponse | null>(null)
const documents = ref<DocumentRecord[]>([])
const uploadedTables = ref<Set<string>>(new Set())
const creating = ref(false)
const validating = ref(false)
const generating = ref(false)
const loadingOutputs = ref(false)
const errorMessage = ref('')
let progressTimer: ReturnType<typeof window.setInterval> | null = null

const requiredTables = computed<RequiredTable[]>(() => {
  return task.value?.required_tables.length ? task.value.required_tables : requirements.value?.required_tables || []
})

const isXlsxTemplate = computed(() => requirements.value?.template_file_type === 'xlsx')

const requiredUploadCount = computed(() => {
  return requiredTables.value.filter((table) => table.required !== false).length
})

const uploadedCount = computed(() => {
  return requiredTables.value.filter((table) => uploadedTables.value.has(table.table_name)).length
})

const allRequiredUploaded = computed(() => {
  if (!task.value || requiredUploadCount.value === 0) {
    return false
  }
  return requiredTables.value
    .filter((table) => table.required !== false)
    .every((table) => uploadedTables.value.has(table.table_name))
})

const activeStep = computed(() => {
  if (generationResult.value) {
    return 4
  }
  if (validationReport.value) {
    return 3
  }
  if (allRequiredUploaded.value) {
    return 2
  }
  if (task.value) {
    return 1
  }
  return 0
})

const uploadProgressText = computed(() => {
  if (!task.value) {
    return '等待任务'
  }
  return `${uploadedCount.value}/${requiredTables.value.length} 已上传`
})

const validationStepText = computed(() => {
  if (!validationReport.value) {
    return '等待校验'
  }
  return validationReport.value.status === 'failed' ? '校验失败' : '校验完成'
})

const generationStepText = computed(() => {
  if (generationProgress.value?.status === 'running') {
    return generationProgressText.value
  }
  if (!generationResult.value) {
    return '等待生成'
  }
  return `成功 ${generationResult.value.success_count}/${generationResult.value.total_rows}`
})

const uploadStatusText = computed(() => {
  if (!task.value) {
    return '待任务'
  }
  return allRequiredUploaded.value ? '已就绪' : '待上传'
})

const canCreateTask = computed(() => {
  return Boolean(selectedTemplateId.value && taskName.value.trim() && !task.value)
})

const canGenerate = computed(() => {
  return Boolean(task.value && validationReport.value && validationReport.value.status !== 'failed' && !generating.value)
})

const generationTitle = computed(() => {
  if (!generationResult.value) {
    return ''
  }
  const result = generationResult.value
  return `生成完成：总数 ${result.total_rows}，成功 ${result.success_count}，失败 ${result.failed_count}`
})

const processedCount = computed(() => {
  const progress = generationProgress.value
  if (!progress) {
    return generationResult.value ? generationResult.value.success_count + generationResult.value.failed_count : 0
  }
  return progress.success_count + progress.failed_count
})

const generationTotal = computed(() => {
  return generationProgress.value?.total_rows || generationResult.value?.total_rows || 0
})

const generationPercent = computed(() => {
  if (!generationTotal.value) {
    return generating.value ? 5 : 0
  }
  return Math.min(100, Math.round((processedCount.value / generationTotal.value) * 100))
})

const generationProgressText = computed(() => {
  if (!generationTotal.value) {
    return generating.value ? '正在准备生成任务...' : '等待生成'
  }
  return `已生成 ${processedCount.value} / ${generationTotal.value} 份`
})

const generationProgressStatus = computed<'success' | 'exception' | undefined>(() => {
  const status = generationProgress.value?.status || generationResult.value?.status
  if (status === 'failed' || status === 'partial_failed') {
    return 'exception'
  }
  if (status === 'completed') {
    return 'success'
  }
  return undefined
})

onBeforeUnmount(stopProgressPolling)

function onRequirementsLoaded(value: TemplateRequirements | null) {
  requirements.value = value
  uploadedTables.value = new Set()
  if (value && !taskName.value) {
    taskName.value = `${value.template_name}_${new Date().toLocaleString()}`
    aiEnabled.value = value.template_file_type !== 'xlsx'
  } else if (value?.template_file_type === 'xlsx') {
    aiEnabled.value = false
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
  const next = new Set(uploadedTables.value)
  next.add(value.table_name)
  uploadedTables.value = next
  validationReport.value = null
  generationResult.value = null
  generationProgress.value = null
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
  if (documents.value.length) {
    try {
      await ElMessageBox.confirm(
        '重新生成可能覆盖已有输出文件，是否继续？',
        '确认重新生成',
        {
          type: 'warning',
          confirmButtonText: '继续生成',
          cancelButtonText: '取消',
        },
      )
    } catch {
      return
    }
  }
  generating.value = true
  errorMessage.value = ''
  generationResult.value = null
  generationProgress.value = null
    startProgressPolling(task.value.task_id)
  try {
    generationResult.value = await generateTask(task.value.task_id)
    const currentProgress = generationProgress.value as TaskProgressResponse | null
    generationProgress.value = {
      task_id: generationResult.value.task_id,
      task_name: task.value.task_name,
      template_id: task.value.template_id,
      template_name: task.value.template_name,
      status: generationResult.value.status,
      ai_enabled: aiEnabled.value,
      main_table: currentProgress?.main_table || requiredTables.value.find((table) => table.role === 'main')?.table_name || '',
      primary_key_field: currentProgress?.primary_key_field || '',
      total_rows: generationResult.value.total_rows,
      success_count: generationResult.value.success_count,
      failed_count: generationResult.value.failed_count,
      warning_count: currentProgress?.warning_count || 0,
      error_count: currentProgress?.error_count || 0,
      task_dir: currentProgress?.task_dir || '',
      validation_report_path: currentProgress?.validation_report_path || '',
      error_message: generationResult.value.error_message,
      created_by: currentProgress?.created_by || 'system',
      created_at: currentProgress?.created_at || new Date().toISOString(),
      updated_at: currentProgress?.updated_at || new Date().toISOString(),
      started_at: currentProgress?.started_at,
      completed_at: currentProgress?.completed_at,
    }
    await refreshOutputs()
    ElMessage.success('生成流程已结束')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '生成失败'
  } finally {
    stopProgressPolling()
    generating.value = false
  }
}

function startProgressPolling(taskId: string) {
  stopProgressPolling()
  pollProgress(taskId)
  progressTimer = window.setInterval(() => {
    pollProgress(taskId)
  }, 1000)
}

function stopProgressPolling() {
  if (progressTimer) {
    window.clearInterval(progressTimer)
    progressTimer = null
  }
}

async function pollProgress(taskId: string) {
  try {
    const progress = await getTask(taskId)
    generationProgress.value = progress
    if (['completed', 'partial_failed', 'failed'].includes(progress.status)) {
      stopProgressPolling()
    }
  } catch {
    // The generate request will surface the main error; polling failures should not interrupt it.
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
.flow-card {
  padding: 18px 24px;
}

.create-layout {
  align-items: start;
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1fr) 320px;
}

.main-flow,
.section {
  display: grid;
  gap: 16px;
}

.section.disabled {
  opacity: 0.74;
}

.section.locked {
  background: #fbfcff;
}

.section-title p {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
  margin: 5px 0 0;
}

.task-form {
  max-width: 760px;
}

.switch-row {
  align-items: center;
  color: var(--color-text-muted);
  display: flex;
  gap: 10px;
}

.generation-progress {
  background: #f8fbff;
  border: 1px solid #d9e5ff;
  border-radius: 8px;
  display: grid;
  gap: 10px;
  padding: 14px;
}

.progress-heading {
  align-items: center;
  color: var(--color-text);
  display: flex;
  justify-content: space-between;
}

.progress-heading span {
  color: var(--color-primary);
  font-weight: 750;
}

.side-summary {
  display: grid;
  gap: 16px;
  position: sticky;
  top: 20px;
}

.side-summary h3 {
  font-size: 16px;
}

.side-summary dl {
  display: grid;
  gap: 12px;
  margin: 0;
}

.side-summary div {
  min-width: 0;
}

.side-summary dt {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 4px;
}

.side-summary dd {
  color: var(--color-text);
  font-weight: 650;
  margin: 0;
  overflow-wrap: anywhere;
}

@media (max-width: 1080px) {
  .create-layout {
    grid-template-columns: 1fr;
  }

  .side-summary {
    position: static;
  }
}
</style>
