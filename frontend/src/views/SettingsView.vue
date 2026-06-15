<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">配置中心</h2>
        <p class="page-desc">集中承载系统配置模块，本阶段仅搭建基础框架。</p>
      </div>
      <el-button @click="checkHealth">检查配置服务</el-button>
    </div>

    <el-alert v-if="healthMessage" :title="healthMessage" type="success" show-icon :closable="false" />
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="page-card settings-card">
      <div class="setting-intro">
        <strong>配置资产管理</strong>
        <span>维护实体 Schema、模板关系、模板文件与 AI 调用配置。这里的变更会影响后续任务创建和校验流程。</span>
      </div>

      <el-tabs v-model="activeTab" class="settings-tabs">
        <el-tab-pane label="实体Schema" name="entity-schema">
          <EntitySchemaConfig />
        </el-tab-pane>
        <el-tab-pane label="模板关系" name="template-relation">
          <TemplateRelationConfig />
        </el-tab-pane>
        <el-tab-pane label="模板文件" name="template-files">
          <TemplateFileManager />
        </el-tab-pane>
        <el-tab-pane label="AI配置" name="ai-config">
          <AIModelConfig />
        </el-tab-pane>
      </el-tabs>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getSettingsHealth } from '../api/settings'
import AIModelConfig from '../components/settings/AIModelConfig.vue'
import EntitySchemaConfig from '../components/settings/EntitySchemaConfig.vue'
import TemplateFileManager from '../components/settings/TemplateFileManager.vue'
import TemplateRelationConfig from '../components/settings/TemplateRelationConfig.vue'

const activeTab = ref('entity-schema')
const healthMessage = ref('')
const errorMessage = ref('')

async function checkHealth() {
  healthMessage.value = ''
  errorMessage.value = ''
  try {
    const health = await getSettingsHealth()
    healthMessage.value = `配置服务状态：${health.status}`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '配置服务检查失败'
  }
}
</script>

<style scoped>
.settings-tabs {
  min-width: 0;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}
</style>
