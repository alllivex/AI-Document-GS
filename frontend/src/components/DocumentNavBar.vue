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
  padding: 16px 24px;
}

.document-title {
  align-items: center;
  display: flex;
  gap: 16px;
  min-width: 0;
}

.document-title h2 {
  font-size: 18px;
  line-height: 1.4;
  margin: 0;
}

.document-title p {
  color: #909399;
  font-size: 13px;
  margin: 4px 0 0;
}
</style>
