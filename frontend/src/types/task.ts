import type { RequiredTable } from './template'

export type TaskStatus =
  | 'created'
  | 'uploaded'
  | 'validating'
  | 'validated'
  | 'validation_failed'
  | 'running'
  | 'completed'
  | 'partial_failed'
  | 'failed'
  | 'deleted'

export type DocumentStatus = 'pending' | 'running' | 'success' | 'failed' | 'ai_partial_failed'
export type AIStatus = 'not_used' | 'success' | 'partial_failed' | 'failed'

export interface CreateTaskPayload {
  task_name: string
  template_id: number
  ai_enabled: boolean
}

export interface CreateTaskResponse {
  task_id: string
  task_name: string
  template_id: number
  template_name: string
  status: TaskStatus
  task_dir: string
  required_tables: RequiredTable[]
  created_at: string
}

export interface UploadedFileResponse {
  task_id: string
  table_name: string
  original_filename: string
  stored_filename: string
  file_path: string
  file_size: number
  row_count: number
  column_count: number
  uploaded_at: string
}

export interface TaskListItem {
  task_id: string
  task_name: string
  template_id: number
  template_name: string
  status: TaskStatus
  ai_enabled: boolean
  main_table: string
  primary_key_field: string
  total_rows: number
  success_count: number
  failed_count: number
  warning_count: number
  error_count: number
  task_dir: string
  validation_report_path: string
  error_message: string
  created_by: string
  created_at: string
  updated_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface GenerateTaskResponse {
  task_id: string
  status: TaskStatus
  total_rows: number
  success_count: number
  failed_count: number
  document_ids: string[]
  error_message: string
}

export type TaskProgressResponse = TaskListItem

export interface DocumentRecord {
  doc_id: string
  task_id: string
  template_id: number
  template_name: string
  primary_key_value: string
  output_filename: string
  output_path: string
  trace_filename: string
  trace_path: string
  preview_filename: string
  preview_path: string
  status: DocumentStatus
  ai_status: AIStatus
  trace_count: number
  ai_block_count: number
  error_message: string
  created_at: string
  updated_at: string
}

export interface TaskOutputsResponse {
  task_id: string
  items: DocumentRecord[]
  total: number
}
