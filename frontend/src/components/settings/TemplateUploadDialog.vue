<template>
  <el-dialog :model-value="modelValue" title="上传新模板" width="560px" @update:model-value="handleVisibleChange">
    <el-form label-width="100px">
      <el-form-item label="模板名称" required>
        <el-input v-model="templateName" placeholder="请输入模板名称" />
      </el-form-item>
      <el-form-item label="模板说明">
        <el-input v-model="description" type="textarea" :rows="3" placeholder="请输入模板说明，可选" />
      </el-form-item>
      <el-form-item label="模板文件" required>
        <el-upload
          accept=".docx"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-button>选择 docx 文件</el-button>
          <template #tip>
            <div class="upload-tip">仅支持 .docx 文件，上传后系统保存为 template_模板ID.docx。</div>
          </template>
        </el-upload>
      </el-form-item>
    </el-form>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <template #footer>
      <el-button @click="handleVisibleChange(false)">取消</el-button>
      <el-button type="primary" :loading="uploading" :disabled="!canUpload" @click="submitUpload">上传</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { UploadFile } from 'element-plus'
import { uploadTemplateFile } from '../../api/settings'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  uploaded: []
}>()

const templateName = ref('')
const description = ref('')
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const errorMessage = ref('')

const canUpload = computed(() => Boolean(templateName.value.trim() && selectedFile.value && !uploading.value))

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
  if (!rawFile.name.toLowerCase().endsWith('.docx')) {
    selectedFile.value = null
    errorMessage.value = '仅支持上传 .docx 模板文件'
    return
  }
  selectedFile.value = rawFile
}

function handleFileRemove() {
  selectedFile.value = null
}

async function submitUpload() {
  if (!selectedFile.value) {
    errorMessage.value = '请选择 .docx 模板文件'
    return
  }
  uploading.value = true
  errorMessage.value = ''
  try {
    await uploadTemplateFile({
      template_name: templateName.value.trim(),
      description: description.value,
      file: selectedFile.value,
    })
    emit('uploaded')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板上传失败'
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  templateName.value = ''
  description.value = ''
  selectedFile.value = null
  uploading.value = false
  errorMessage.value = ''
}
</script>

<style scoped>
.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 6px;
}
</style>
