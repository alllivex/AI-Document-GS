<template>
  <div class="document-nav">
    <div class="document-title">
      <el-button @click="$emit('back')">返回结果</el-button>
      <div class="title-copy">
        <span class="eyebrow">Trace Review</span>
        <h2>{{ title || '文档溯源预览' }}</h2>
        <p v-if="outputFile">{{ outputFile }}</p>
      </div>
    </div>
    <div class="nav-actions">
      <span class="trace-tip">点击高亮内容查看来源</span>
      <el-button type="primary" :disabled="!docId" @click="$emit('download')">{{ downloadLabel }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  docId: string
  title?: string
  outputFile?: string
}>()

const downloadLabel = computed(() => props.outputFile?.toLowerCase().endsWith('.xlsx') ? '下载 Excel' : '下载 Word')

defineEmits<{
  back: []
  download: []
}>()
</script>

<style scoped>
.document-nav {
  align-items: center;
  background: rgba(255, 255, 255, 0.94);
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex: 0 0 auto;
  gap: 16px;
  justify-content: space-between;
  min-height: var(--document-nav-height, 76px);
  padding: 14px 24px;
  position: relative;
  z-index: 20;
}

.document-title {
  align-items: center;
  display: flex;
  flex: 1;
  gap: 16px;
  min-width: 0;
}

.title-copy {
  min-width: 0;
}

.eyebrow {
  color: var(--color-primary);
  display: block;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin-bottom: 2px;
  text-transform: uppercase;
}

.document-title h2 {
  color: var(--color-text);
  font-size: 18px;
  font-weight: 750;
  line-height: 1.35;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-title p {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 4px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-actions {
  align-items: center;
  display: flex;
  flex: 0 0 auto;
  gap: 12px;
}

.trace-tip {
  background: var(--color-primary-soft);
  border: 1px solid #d9e5ff;
  border-radius: 999px;
  color: #1f4fbd;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
}

@media (max-width: 960px) {
  .document-nav {
    align-items: flex-start;
    flex-direction: column;
  }

  .document-title,
  .nav-actions {
    width: 100%;
  }

  .nav-actions {
    justify-content: space-between;
  }
}
</style>
