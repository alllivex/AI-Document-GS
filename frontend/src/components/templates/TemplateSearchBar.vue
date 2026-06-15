<template>
  <el-form class="page-toolbar search-bar" @submit.prevent>
    <div class="toolbar-left">
      <el-input
        v-model="keyword"
        clearable
        placeholder="按模板名称搜索"
        @clear="emitSearch"
        @keyup.enter="emitSearch"
      />
      <span class="search-hint">仅显示已启用模板</span>
    </div>
    <div class="toolbar-right">
      <el-button type="primary" :loading="loading" @click="emitSearch">搜索</el-button>
    </div>
  </el-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  search: [value: string]
}>()

const keyword = ref('')

function emitSearch() {
  emit('search', keyword.value)
}
</script>

<style scoped>
.search-bar {
  background: #f8fafc;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 0;
  padding: 12px;
}

.search-bar .el-input {
  width: 360px;
}

.search-hint {
  background: var(--color-primary-soft);
  border: 1px solid #d9e5ff;
  border-radius: 999px;
  color: #1f4fbd;
  font-size: 12px;
  font-weight: 700;
  padding: 7px 10px;
}
</style>
