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
      <el-button disabled>筛选</el-button>
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
  margin-bottom: 0;
}

.search-bar .el-input {
  width: 360px;
}
</style>
