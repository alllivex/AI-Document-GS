<template>
  <AppLayout>
    <div v-if="runtimeError" class="runtime-error">
      页面运行错误：{{ runtimeError }}
    </div>
    <router-view />
  </AppLayout>
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'
import AppLayout from './components/layout/AppLayout.vue'

const runtimeError = ref('')

onErrorCaptured((error) => {
  runtimeError.value = error instanceof Error ? error.message : String(error)
  return false
})
</script>

<style scoped>
.runtime-error {
  background: #fef0f0;
  border-bottom: 1px solid #fecdca;
  color: #b42318;
  padding: 12px 24px;
}
</style>
