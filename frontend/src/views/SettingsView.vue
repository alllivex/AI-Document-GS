<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2>配置中心</h2>
        <p>集中承载系统配置模块，本阶段仅搭建基础框架。</p>
      </div>
      <el-button @click="checkHealth">检查配置服务</el-button>
    </div>

    <el-alert v-if="healthMessage" :title="healthMessage" type="success" show-icon :closable="false" />
    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

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
.page {
  display: grid;
  gap: 16px;
  padding: 24px;
}

.page-header {
  align-items: flex-start;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.page-header h2 {
  margin: 0 0 6px;
}

.page-header p {
  color: #606266;
  margin: 0;
}

.settings-tabs {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 16px;
}

.placeholder {
  color: #606266;
  padding: 24px 0;
}
</style>
