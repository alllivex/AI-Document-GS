<template>
  <el-dialog
    :model-value="modelValue"
    title="更换模板文件"
    width="520px"
    @update:model-value="handleVisibleChange"
  >
    <el-alert
      v-if="template"
      :title="`当前模板：${template.template_name}`"
      type="info"
      show-icon
      :closable="false"
    />

    <el-form class="replace-form" label-width="96px">
      <el-form-item label="新模板文件" required>
        <el-upload
          :accept="requiredSuffix"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-button>选择 {{ requiredSuffix }} 文件</el-button>
          <template #tip>
            <div class="upload-tip">只能替换为同类型模板；更换前会校验变量，失败时不会覆盖旧文件。</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <template #footer>
      <el-button @click="handleVisibleChange(false)">取消</el-button>
      <el-button type="primary" :loading="replacing" :disabled="!canReplace" @click="submitReplace">
        确认更换
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { UploadFile } from 'element-plus'
import { replaceTemplateFile } from '../../api/settings'
import type { TemplateFileRecord } from '../../types/settings'

const props = defineProps<{
  modelValue: boolean
  template: TemplateFileRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  replaced: []
}>()

const selectedFile = ref<File | null>(null)
const replacing = ref(false)
const errorMessage = ref('')

const canReplace = computed(() => Boolean(props.template && selectedFile.value && !replacing.value))
const requiredSuffix = computed(() => props.template?.template_file_type === 'xlsx' ? '.xlsx' : '.docx')

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      resetForm()
    }
  },
)

function handleVisibleChange(value: boolean) {
  emit('update:modelValue', value)
}

function handleFileChange(uploadFile: UploadFile) {
  errorMessage.value = ''
  const rawFile = uploadFile.raw
  if (!rawFile) {
    selectedFile.value = null
    return
  }
  if (!rawFile.name.toLowerCase().endsWith(requiredSuffix.value)) {
    selectedFile.value = null
    errorMessage.value = `请选择 ${requiredSuffix.value} 模板文件`
    return
  }
  selectedFile.value = rawFile
}

function handleFileRemove() {
  selectedFile.value = null
}

async function submitReplace() {
  if (!props.template || !selectedFile.value) {
    errorMessage.value = `请选择 ${requiredSuffix.value} 模板文件`
    return
  }
  replacing.value = true
  errorMessage.value = ''
  try {
    await replaceTemplateFile(props.template.template_id, selectedFile.value)
    emit('replaced')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板更换失败'
  } finally {
    replacing.value = false
  }
}

function resetForm() {
  selectedFile.value = null
  replacing.value = false
  errorMessage.value = ''
}
</script>

<style scoped>
.replace-form {
  margin-top: 16px;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
</style>
