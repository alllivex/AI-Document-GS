<template>
  <main class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">模板中心</h2>
        <p class="page-desc">选择业务模板，查看依赖表摘要，并发起文档生成任务。</p>
      </div>
    </div>

    <section class="page-card">
      <TemplateSearchBar :loading="loading" @search="handleSearch" />
    </section>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon :closable="false" />

    <el-empty v-if="!loading && templates.length === 0" description="暂无匹配模板" />

    <div v-else v-loading="loading" class="template-grid">
      <TemplateCard
        v-for="template in templates"
        :key="template.template_id"
        :template="template"
        @view-detail="openDetail"
        @use-template="useTemplate"
      />
    </div>

    <TemplateDetailDialog
      v-model="detailVisible"
      :detail="currentDetail"
      :loading="detailLoading"
      @use-template="useTemplate"
    />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import TemplateCard from '../components/templates/TemplateCard.vue'
import TemplateDetailDialog from '../components/templates/TemplateDetailDialog.vue'
import TemplateSearchBar from '../components/templates/TemplateSearchBar.vue'
import { getTemplate, listTemplates } from '../api/templates'
import type { TemplateDetail, TemplateListItem } from '../types/template'

const router = useRouter()
const templates = ref<TemplateListItem[]>([])
const currentDetail = ref<TemplateDetail | null>(null)
const loading = ref(false)
const detailLoading = ref(false)
const detailVisible = ref(false)
const errorMessage = ref('')
const searchText = ref('')

onMounted(() => {
  loadTemplates()
})

async function loadTemplates() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await listTemplates({ search: searchText.value || undefined, active_only: true })
    templates.value = response.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板列表加载失败'
  } finally {
    loading.value = false
  }
}

function handleSearch(value: string) {
  searchText.value = value.trim()
  loadTemplates()
}

async function openDetail(templateId: number) {
  detailVisible.value = true
  detailLoading.value = true
  currentDetail.value = null
  errorMessage.value = ''
  try {
    currentDetail.value = await getTemplate(templateId)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模板详情加载失败'
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

function useTemplate(templateId: number) {
  router.push({ path: '/tasks/new', query: { template_id: String(templateId) } })
}
</script>

<style scoped>
.template-grid {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  min-height: 160px;
}
</style>
