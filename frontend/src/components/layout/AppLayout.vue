<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">AI智能文档生成系统</div>
      <el-menu mode="horizontal" router :default-active="activeMenu" class="nav-menu">
        <el-menu-item index="/tasks">任务中心</el-menu-item>
        <el-menu-item index="/templates">模板中心</el-menu-item>
        <el-menu-item index="/settings">配置中心</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="app-main">
      <slot />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/templates')) {
    return '/templates'
  }
  if (route.path.startsWith('/settings')) {
    return '/settings'
  }
  return '/tasks'
})
</script>

<style scoped>
.app-shell {
  --app-header-height: 60px;
  --document-nav-height: 73px;
  --trace-sticky-top: calc(var(--app-header-height) + var(--document-nav-height));
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
}

.app-header {
  align-items: center;
  background: #fff;
  border-bottom: 1px solid #edf0f5;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
  display: flex;
  flex: 0 0 var(--app-header-height);
  gap: 24px;
  height: var(--app-header-height);
  padding: 0 24px;
  position: relative;
  z-index: 30;
}

.brand {
  color: #1f2937;
  font-size: 18px;
  font-weight: 650;
  white-space: nowrap;
}

.nav-menu {
  border-bottom: 0;
  flex: 1;
}

.nav-menu :deep(.el-menu-item) {
  color: #475467;
  font-weight: 600;
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: #2563eb;
}

.app-main {
  background: #f4f7fb;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
}
</style>
