<template>
  <main class="page">
    <el-alert v-if="healthMessage" :title="healthMessage" type="success" show-icon :closable="false" />
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <section class="page-card settings-card">
      <div class="settings-toolbar">
        <div>
          <h2>配置中心</h2>
          <p>维护系统基础配置与模板资产。</p>
        </div>
        <el-button @click="checkHealth">检查配置服务</el-button>
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

.settings-card {
  display: grid;
  gap: 16px;
}

.settings-toolbar {
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding-bottom: 14px;
}

.settings-toolbar h2 {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 750;
  margin: 0;
}

.settings-toolbar p {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 5px 0 0;
}

@media (max-width: 760px) {
  .settings-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
