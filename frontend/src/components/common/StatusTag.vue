<template>
  <span class="status-tag" :class="`status-${tone}`">
    <span class="status-dot" />
    <slot>{{ label || status }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    status?: string
    label?: string
    type?: 'success' | 'warning' | 'danger' | 'processing' | 'default'
  }>(),
  {
    status: 'default',
    label: '',
    type: undefined,
  },
)

const tone = computed(() => {
  if (props.type) {
    return props.type
  }

  const normalized = props.status.toLowerCase()
  if (['success', 'completed', 'validated', 'passed', 'available', 'active'].includes(normalized)) {
    return 'success'
  }
  if (['warning', 'partial_failed', 'passed_with_warnings', 'uploaded'].includes(normalized)) {
    return 'warning'
  }
  if (['danger', 'error', 'failed', 'validation_failed', 'unavailable', 'deleted'].includes(normalized)) {
    return 'danger'
  }
  if (['processing', 'running', 'validating', 'uploading', 'created'].includes(normalized)) {
    return 'processing'
  }
  return 'default'
})
</script>

<style scoped>
.status-tag {
  align-items: center;
  border: 1px solid transparent;
  border-radius: 999px;
  display: inline-flex;
  font-size: 12px;
  font-weight: 600;
  gap: 6px;
  line-height: 1;
  padding: 6px 10px;
  white-space: nowrap;
}

.status-dot {
  border-radius: 50%;
  height: 6px;
  width: 6px;
}

.status-success {
  background: #ecfdf3;
  border-color: #abefc6;
  color: #067647;
}

.status-success .status-dot {
  background: #12b76a;
}

.status-warning {
  background: #fffaeb;
  border-color: #fedf89;
  color: #b54708;
}

.status-warning .status-dot {
  background: #f79009;
}

.status-danger {
  background: #fef3f2;
  border-color: #fecdca;
  color: #b42318;
}

.status-danger .status-dot {
  background: #f04438;
}

.status-processing {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.status-processing .status-dot {
  background: #2563eb;
}

.status-default {
  background: #f2f4f7;
  border-color: #e4e7ec;
  color: #475467;
}

.status-default .status-dot {
  background: #98a2b3;
}
</style>
