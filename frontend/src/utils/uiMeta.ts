import type { TaskStatus } from '../types/task'
import type { TraceKind } from '../types/trace'

export interface TaskStatusOption {
  value: TaskStatus | 'all'
  label: string
}

export interface TraceKindMeta {
  label: string
  tone: 'field' | 'condition' | 'loop' | 'ai'
  description: string
}

export const taskStatusOptions: TaskStatusOption[] = [
  { value: 'all', label: '全部状态' },
  { value: 'created', label: '已创建' },
  { value: 'uploaded', label: '已上传' },
  { value: 'validating', label: '校验中' },
  { value: 'validated', label: '已校验' },
  { value: 'validation_failed', label: '校验失败' },
  { value: 'running', label: '生成中' },
  { value: 'completed', label: '已完成' },
  { value: 'partial_failed', label: '部分失败' },
  { value: 'failed', label: '失败' },
  { value: 'deleted', label: '已删除' },
]

export function taskStatusText(status: TaskStatus | string) {
  return taskStatusOptions.find((option) => option.value === status)?.label || status
}

export function isTaskActive(status: TaskStatus) {
  return ['created', 'uploaded', 'validating', 'validated', 'running'].includes(status)
}

export function traceKindMeta(kind: TraceKind | string): TraceKindMeta {
  const map: Record<TraceKind, TraceKindMeta> = {
    field: {
      label: '字段来源',
      tone: 'field',
      description: '来自 Excel 原始业务数据',
    },
    condition: {
      label: '条件判断',
      tone: 'condition',
      description: '由模板条件表达式决定输出',
    },
    loop: {
      label: '循环表格',
      tone: 'loop',
      description: '由一对多明细数据展开生成',
    },
    ai: {
      label: 'AI 生成',
      tone: 'ai',
      description: '由提示词和上下文变量生成',
    },
  }

  return map[kind as TraceKind] || map.field
}
