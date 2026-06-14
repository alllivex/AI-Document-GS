<template>
  <el-form class="search-bar" @submit.prevent>
    <el-input
      v-model="keyword"
      clearable
      placeholder="按模板名称搜索"
      @clear="emitSearch"
      @keyup.enter="emitSearch"
    />
    <el-button type="primary" :loading="loading" @click="emitSearch">搜索</el-button>
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
  align-items: center;
  display: grid;
  gap: 12px;
  grid-template-columns: minmax(220px, 420px) auto;
  justify-content: start;
}
</style>
