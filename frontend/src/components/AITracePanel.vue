<template>
  <div class="trace-section">
    <el-tag type="warning">AI生成段落</el-tag>

    <el-descriptions :column="1" border>
      <el-descriptions-item label="AI Block">{{ trace.block_id }}</el-descriptions-item>
      <el-descriptions-item label="生成状态">{{ statusText(trace.status) }}</el-descriptions-item>
      <el-descriptions-item label="模型">{{ trace.model || '-' }}</el-descriptions-item>
      <el-descriptions-item label="生成时间">{{ formatTime(trace.completed_at || trace.started_at) }}</el-descriptions-item>
    </el-descriptions>

    <section class="detail-block">
      <h4>原始模板段落</h4>
      <pre>{{ trace.original_block_text || '-' }}</pre>
    </section>

    <section class="detail-block">
      <h4>原始 Prompt</h4>
      <pre>{{ trace.prompt_template || '-' }}</pre>
    </section>

    <section class="detail-block">
      <h4>渲染后 Prompt</h4>
      <pre>{{ trace.prompt_rendered || '-' }}</pre>
    </section>

    <section class="detail-block">
      <h4>使用的数据字段</h4>
      <el-table :data="trace.input_variables" border size="small">
        <el-table-column label="字段" min-width="180">
          <template #default="{ row }">
            <button v-if="row.trace_id" class="link-button" type="button" @click="$emit('select-trace', row.trace_id)">
              {{ displayName(row.field_name_cn, row.var_path) }}
            </button>
            <span v-else>{{ displayName(row.field_name_cn, row.var_path) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="展示值" min-width="100" prop="display_value" />
        <el-table-column label="来源" min-width="150">
          <template #default="{ row }">
            {{ row.source_file || '-' }}<span v-if="row.excel_row_number"> 第 {{ row.excel_row_number }} 行</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="detail-block">
      <h4>知识库标记</h4>
      <el-empty v-if="!trace.knowledge_refs.length" description="未检测到知识库标记" />
      <el-alert
        v-for="ref in trace.knowledge_refs"
        :key="ref.kb_name"
        :title="`${ref.kb_name}：仅检测到知识库标记，当前未执行知识库检索。`"
        type="info"
        :closable="false"
      />
    </section>

    <section class="detail-block">
      <h4>AI生成结果</h4>
      <pre>{{ trace.generated_text || '-' }}</pre>
      <el-alert v-if="trace.error_message" :title="trace.error_message" type="error" :closable="false" />
    </section>
  </div>
</template>

<script setup lang="ts">
import type { AITraceDetail } from '../types/trace'

defineProps<{
  trace: AITraceDetail
}>()

defineEmits<{
  'select-trace': [traceId: string]
}>()

function displayName(cn?: string, name?: string) {
  if (cn && name) {
    return `${cn}（${name}）`
  }
  return cn || name || '-'
}

function statusText(status: string) {
  if (status === 'success') {
    return '成功'
  }
  if (status === 'failed') {
    return '失败'
  }
  return '已跳过'
}

function formatTime(value?: string | null) {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString()
}
</script>

<style scoped>
.trace-section {
  display: grid;
  gap: 14px;
}

.detail-block {
  display: grid;
  gap: 8px;
}

.detail-block h4 {
  font-size: 14px;
  margin: 0;
}

pre {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  line-height: 1.6;
  margin: 0;
  max-height: 260px;
  overflow: auto;
  padding: 10px;
  white-space: pre-wrap;
  word-break: break-word;
}

.link-button {
  background: transparent;
  border: 0;
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  padding: 0;
  text-align: left;
}
</style>
