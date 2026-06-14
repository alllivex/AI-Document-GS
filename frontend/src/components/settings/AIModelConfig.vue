<template>
  <section class="ai-config">
    <div class="toolbar">
      <div>
        <h3>AI配置</h3>
        <p>当前 MVP 使用 DeepSeek OpenAI-compatible API，API Key 通过环境变量配置。</p>
      </div>
      <el-tag :type="config?.status === 'available' ? 'success' : 'danger'">
        {{ config?.status === 'available' ? '可用' : '不可用' }}
      </el-tag>
    </div>

    <el-alert
      v-if="config && !config.api_key_configured"
      title="当前未配置 API Key，请在环境变量 DEEPSEEK_API_KEY 中配置。"
      type="warning"
      show-icon
      :closable="false"
    />
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />
    <el-alert v-if="resultMessage" :title="resultMessage" :type="resultType" show-icon :closable="false" />

    <el-form v-loading="loading" class="config-form" label-width="140px">
      <el-form-item label="Provider">
        <el-input v-model="form.provider" placeholder="deepseek" />
      </el-form-item>
      <el-form-item label="模型名称">
        <el-input v-model="form.model_name" placeholder="deepseek-chat" />
      </el-form-item>
      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" placeholder="https://api.deepseek.com/v1" />
      </el-form-item>
      <el-form-item label="Temperature">
        <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" />
      </el-form-item>
      <el-form-item label="Timeout">
        <el-input-number v-model="form.timeout_seconds" :min="1" :max="600" :step="5" />
        <span class="suffix">秒</span>
      </el-form-item>
      <el-form-item label="启用配置">
        <el-switch v-model="form.is_active" />
      </el-form-item>
      <el-form-item label="API Key状态">
        <el-tag :type="config?.api_key_configured ? 'success' : 'info'">
          {{ config?.api_key_configured ? '已配置' : '未配置' }}
        </el-tag>
      </el-form-item>
      <el-form-item label="API Key来源">
        <span>{{ apiKeySourceText }}</span>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
        <el-button :loading="testing" @click="testConnection">测试连接</el-button>
      </el-form-item>
    </el-form>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAIConfig, testAIConfig, updateAIConfig } from '../../api/settings'
import type { AIConfig } from '../../types/settings'

const config = ref<AIConfig | null>(null)
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const errorMessage = ref('')
const resultMessage = ref('')
const resultStatus = ref<'success' | 'failed'>('success')

const form = reactive({
  provider: 'deepseek',
  model_name: 'deepseek-chat',
  base_url: 'https://api.deepseek.com/v1',
  temperature: 0.2,
  timeout_seconds: 60,
  is_active: true,
})

const apiKeySourceText = computed(() => {
  if (!config.value) {
    return '-'
  }
  const map: Record<AIConfig['api_key_source'], string> = {
    env: '环境变量',
    db: '页面配置',
    none: '未配置',
  }
  return map[config.value.api_key_source]
})

const resultType = computed(() => (resultStatus.value === 'success' ? 'success' : 'warning'))

onMounted(loadConfig)

async function loadConfig() {
  loading.value = true
  errorMessage.value = ''
  try {
    const value = await getAIConfig()
    applyConfig(value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'AI配置加载失败'
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  errorMessage.value = ''
  resultMessage.value = ''
  try {
    const value = await updateAIConfig({
      provider: form.provider,
      model_name: form.model_name,
      base_url: form.base_url,
      temperature: form.temperature,
      timeout_seconds: form.timeout_seconds,
      is_active: form.is_active,
    })
    applyConfig(value)
    ElMessage.success('AI配置已保存')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'AI配置保存失败'
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  testing.value = true
  errorMessage.value = ''
  resultMessage.value = ''
  try {
    const result = await testAIConfig()
    resultStatus.value = result.status
    resultMessage.value = result.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'AI连接测试失败'
  } finally {
    testing.value = false
  }
}

function applyConfig(value: AIConfig) {
  config.value = value
  form.provider = value.provider
  form.model_name = value.model_name
  form.base_url = value.base_url
  form.temperature = value.temperature
  form.timeout_seconds = value.timeout_seconds
  form.is_active = value.is_active
}
</script>

<style scoped>
.ai-config {
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

.config-form {
  max-width: 760px;
}

.suffix {
  color: #606266;
  margin-left: 8px;
}
</style>
