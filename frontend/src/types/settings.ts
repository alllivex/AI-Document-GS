export interface SettingsHealth {
  status: 'ok'
}

export interface TemplateFileRecord {
  template_id: number
  template_name: string
  template_file: string
  original_filename: string
  template_path: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UploadTemplateFilePayload {
  template_name: string
  description?: string
  file: File
}

export interface EntitySchemaFieldRecord {
  id: number
  table_name: string
  table_name_cn: string
  field_name: string
  field_name_cn: string
  data_type: string
  is_primary_key: boolean
  required: boolean
  display_format: string
  description: string
  is_active: boolean
}

export interface EntitySchemaTableSummary {
  table_name: string
  table_name_cn: string
  field_count: number
  primary_key_fields: string[]
  required_field_count: number
}

export interface ListEntitySchemaParams {
  table_name?: string
  keyword?: string
  page?: number
  page_size?: number
}

export interface EntitySchemaImportSummary {
  total_rows: number
  create_count: number
  update_count: number
  skip_count: number
  error_count: number
  warning_count: number
}

export type EntitySchemaImportAction = 'create' | 'update' | 'skip' | 'error'
export type EntitySchemaImportLevel = 'info' | 'warning' | 'error'

export interface EntitySchemaImportItem {
  row_number: number
  action: EntitySchemaImportAction
  level: EntitySchemaImportLevel
  message: string
}

export interface EntitySchemaImportPreview {
  import_id: string
  summary: EntitySchemaImportSummary
  items: EntitySchemaImportItem[]
  can_commit: boolean
}

export interface TemplateRelationRecord {
  id: number
  template_id: number
  template_name: string
  template_file: string
  table_name: string
  table_name_cn: string
  role: 'main' | 'aux'
  relation_type: 'main' | 'one_to_one' | 'one_to_many'
  main_join_key: string
  table_join_key: string
  required: boolean
  description: string
}

export interface ListTemplateRelationsParams {
  template_id?: number
  keyword?: string
  page?: number
  page_size?: number
}

export interface TemplateRelationImportSummary {
  total_rows: number
  create_count: number
  update_count: number
  error_count: number
  warning_count: number
}

export type TemplateRelationImportAction = 'create' | 'update' | 'skip' | 'error'
export type TemplateRelationImportLevel = 'info' | 'warning' | 'error'

export interface TemplateRelationImportItem {
  row_number: number
  action: TemplateRelationImportAction
  level: TemplateRelationImportLevel
  message: string
}

export interface TemplateRelationImportPreview {
  import_id: string
  summary: TemplateRelationImportSummary
  items: TemplateRelationImportItem[]
  can_commit: boolean
}

export interface AIConfig {
  provider: string
  model_name: string
  base_url: string
  temperature: number
  timeout_seconds: number
  api_key_configured: boolean
  api_key_source: 'env' | 'db' | 'none'
  is_active: boolean
  status: 'available' | 'unavailable'
}

export interface AIConfigUpdatePayload {
  provider: string
  model_name: string
  base_url: string
  temperature: number
  timeout_seconds: number
  is_active: boolean
}

export interface AIConfigTestResult {
  status: 'success' | 'failed'
  message: string
}
