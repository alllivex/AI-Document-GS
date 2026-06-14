<template>
  <div class="document-nav">
    <div class="document-title">
      <el-button @click="$emit('back')">返回任务结果</el-button>
      <div>
        <h2>{{ title || '文档溯源预览' }}</h2>
        <p v-if="outputFile">{{ outputFile }}</p>
      </div>
    </div>
    <el-button type="primary" :disabled="!docId" @click="$emit('download')">下载当前 Word</el-button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  docId: string
  title?: string
  outputFile?: string
}>()

defineEmits<{
  back: []
  download: []
}>()
</script>

<style scoped>
.document-nav {
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex: 0 0 auto;
  min-height: var(--document-nav-height, 73px);
  padding: 16px 24px;
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

.document-title > div {
  min-width: 0;
}

.document-title h2 {
  font-size: 18px;
  line-height: 1.4;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-title p {
  color: #909399;
  font-size: 13px;
  margin: 4px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-nav > .el-button {
  flex: 0 0 auto;
}

@media (max-width: 960px) {
  .document-nav {
    align-items: flex-start;
    flex-direction: column;
  }

  .document-title {
    width: 100%;
  }
}
</style>
