<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">AI 智能文档生成系统</div>
      <el-menu mode="horizontal" router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/tasks">任务列表</el-menu-item>
        <el-menu-item index="/tasks/create">新建任务</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <div v-if="runtimeError" class="runtime-error">
        页面运行错误：{{ runtimeError }}
      </div>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'

const runtimeError = ref('')

onErrorCaptured((error) => {
  runtimeError.value = error instanceof Error ? error.message : String(error)
  return false
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.app-header {
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  gap: 24px;
  padding: 0 24px;
}

.brand {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: 0;
  flex: 1;
}

.app-main {
  padding: 0;
}
</style>
