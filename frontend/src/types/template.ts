export type TableRole = 'main' | 'aux'
export type RelationType = 'main' | 'one_to_one' | 'one_to_many'
export type DataType = 'string' | 'number' | 'integer' | 'date' | 'datetime' | 'percent' | 'boolean' | 'amount'
export type TemplateFileType = 'docx' | 'xlsx'

export interface FieldDefinition {
  table_name: string
  table_name_cn: string
  field_name: string
  field_name_cn: string
  data_type: DataType
  is_primary_key: boolean
  required: boolean
  display_format: string
  description: string
  created_at?: string | null
  updated_at?: string | null
}

export interface RequiredTable {
  table_name: string
  table_name_cn: string
  role: TableRole
  relation_type: RelationType
  main_join_key: string
  table_join_key: string
  required: boolean
}

export interface TemplateInfo {
  template_id: number
  template_name: string
  template_file: string
  template_path: string
  template_file_type: TemplateFileType
  main_table: string
  output_name_pattern: string
  ai_enabled_default: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TemplateListItem {
  template_id: number
  template_name: string
  template_file: string
  template_path: string
  template_file_type: TemplateFileType
  main_table: string
  main_table_cn: string
  aux_table_count: number
  required_table_count: number
  is_active: boolean
  updated_at: string
}

export interface TemplateTableSummary {
  table_name: string
  table_name_cn: string
  role: TableRole
  relation_type: RelationType
  required: boolean
  main_join_key: string
  table_join_key: string
}

export interface TemplateDetail {
  template_id: number
  template_name: string
  template_file: string
  template_path: string
  template_file_type: TemplateFileType
  main_table: TemplateTableSummary
  aux_tables: TemplateTableSummary[]
  is_active: boolean
  updated_at: string
}

export interface TemplateRequirements {
  template_id: number
  template_name: string
  template_file: string
  template_path: string
  template_file_type: TemplateFileType
  main_table: string
  primary_key_field: string
  required_tables: RequiredTable[]
  fields: FieldDefinition[]
}
