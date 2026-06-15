<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="header-inner">
        <div class="brand-block">
          <div class="brand-mark">AI</div>
          <div>
            <div class="brand">智能文档生成系统</div>
            <div class="brand-subtitle">Document Automation Workspace</div>
          </div>
        </div>

        <el-menu mode="horizontal" router :default-active="activeMenu" class="nav-menu">
          <el-menu-item index="/tasks">任务中心</el-menu-item>
          <el-menu-item index="/templates">模板中心</el-menu-item>
          <el-menu-item index="/settings">配置中心</el-menu-item>
        </el-menu>

        <div class="module-chip">
          <span class="module-dot" />
          {{ activeModule }}
        </div>
      </div>
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

const activeModule = computed(() => {
  if (activeMenu.value === '/templates') {
    return '模板资产'
  }
  if (activeMenu.value === '/settings') {
    return '系统配置'
  }
  return '任务工作台'
})
</script>

<style scoped>
.app-shell {
  --app-header-height: 68px;
  --document-nav-height: 76px;
  --trace-sticky-top: calc(var(--app-header-height) + var(--document-nav-height));
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
}

.app-header {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 0 rgba(20, 32, 56, 0.03);
  flex: 0 0 var(--app-header-height);
  height: var(--app-header-height);
  padding: 0 24px;
  position: relative;
  z-index: 30;
}

.header-inner {
  align-items: center;
  display: flex;
  gap: 26px;
  height: 100%;
  margin: 0 auto;
  max-width: var(--page-max-width);
}

.brand-block {
  align-items: center;
  display: flex;
  flex: 0 0 auto;
  gap: 12px;
  min-width: 250px;
}

.brand-mark {
  align-items: center;
  background: linear-gradient(135deg, #2458d3, #5282ff);
  border-radius: 8px;
  box-shadow: 0 8px 18px rgba(36, 88, 211, 0.26);
  color: #fff;
  display: flex;
  font-size: 13px;
  font-weight: 800;
  height: 34px;
  justify-content: center;
  width: 34px;
}

.brand {
  color: var(--color-text);
  font-size: 16px;
  font-weight: 750;
  white-space: nowrap;
}

.brand-subtitle {
  color: var(--color-text-muted);
  font-size: 11px;
  margin-top: 2px;
  white-space: nowrap;
}

.nav-menu {
  background: transparent;
  border-bottom: 0;
  flex: 1;
  height: 100%;
}

.nav-menu :deep(.el-menu-item) {
  border-bottom: 0;
  color: var(--color-text-secondary);
  font-weight: 700;
  height: var(--app-header-height);
  padding: 0 18px;
}

.nav-menu :deep(.el-menu-item.is-active) {
  color: var(--color-primary);
}

.nav-menu :deep(.el-menu-item.is-active::after) {
  background: var(--color-primary);
  border-radius: 999px 999px 0 0;
  bottom: 0;
  content: "";
  height: 3px;
  left: 18px;
  position: absolute;
  right: 18px;
}

.module-chip {
  align-items: center;
  background: var(--color-primary-soft);
  border: 1px solid #d9e5ff;
  border-radius: 999px;
  color: #1f4fbd;
  display: inline-flex;
  flex: 0 0 auto;
  font-size: 12px;
  font-weight: 700;
  gap: 7px;
  padding: 7px 11px;
}

.module-dot {
  background: #2458d3;
  border-radius: 50%;
  height: 6px;
  width: 6px;
}

.app-main {
  background: transparent;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0;
}

@media (max-width: 900px) {
  .brand-subtitle,
  .module-chip {
    display: none;
  }

  .brand-block {
    min-width: auto;
  }
}
</style>
