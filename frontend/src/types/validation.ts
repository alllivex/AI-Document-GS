export type ValidationLevel = 'error' | 'warning' | 'info'
export type ValidationStatus = 'passed' | 'failed' | 'passed_with_warnings'

export interface ValidationSummary {
  error_count: number
  warning_count: number
  info_count: number
}

export interface ValidationItem {
  level: ValidationLevel
  code: string
  message: string
  table_name?: string | null
  field_name?: string | null
  template_id?: number | null
  template_file?: string | null
  suggestion?: string | null
  detail?: Record<string, unknown> | null
}

export interface ValidateTaskResponse {
  task_id: string
  status: ValidationStatus
  report_path: string
  summary: ValidationSummary
  items: ValidationItem[]
}
