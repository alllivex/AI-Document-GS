export type TraceKind = 'field' | 'condition' | 'loop' | 'ai'
export type HighlightReason = 'clicked' | 'used_in_condition' | 'used_in_loop' | 'none'

export interface SourceRecordField {
  field_name: string
  field_name_cn: string
  raw_value: string | number | boolean | null
  display_value: string
  value_type: string
  excel_column_letter?: string | null
  is_highlighted: boolean
  highlight_reason: HighlightReason
}

export interface SourceRecordView {
  table_name: string
  table_name_cn: string
  source_file: string
  row_index: number
  excel_row_number: number
  relation_type: 'main' | 'one_to_one' | 'one_to_many'
  fields: SourceRecordField[]
}

export interface BaseTraceDetail {
  trace_id: string
  trace_kind: TraceKind
  task_id: string
  doc_id: string
  primary_key_value: string
}

export interface FieldTraceDetail extends BaseTraceDetail {
  trace_kind: 'field'
  original_var_path?: string | null
  canonical_var_path: string
  var_path: string
  table_name: string
  table_name_cn: string
  field_name: string
  field_name_cn: string
  source_record: SourceRecordView
}

export interface ConditionTraceDetail extends BaseTraceDetail {
  trace_kind: 'condition'
  expression: string
  used_variables: string[]
  evaluated_result: boolean
  selected_branch: 'if' | 'else'
  expected_output_text: string
  actual_output_text: string
  is_consistent: boolean
  source_records: SourceRecordView[]
}

export interface LoopTraceDetail extends BaseTraceDetail {
  trace_kind: 'loop'
  table_name: string
  table_name_cn: string
  loop_alias: string
  used_fields: string[]
  matched_row_count: number
  source_records: SourceRecordView[]
}

export interface AIInputVariable {
  original_var_path?: string | null
  canonical_var_path?: string | null
  var_path: string
  table_name: string
  table_name_cn: string
  field_name: string
  field_name_cn: string
  raw_value: string | number | boolean | null
  display_value: string
  trace_id?: string | null
  source_file: string
  excel_row_number?: number | null
  excel_column_letter?: string | null
}

export interface KnowledgeReference {
  kb_name: string
  retrieval_enabled: boolean
  chunk_id?: string | null
  doc_name?: string | null
  score?: number | null
  excerpt?: string | null
}

export interface AITraceDetail extends BaseTraceDetail {
  trace_kind: 'ai'
  block_id: string
  marker: string
  status: 'success' | 'failed' | 'skipped'
  original_block_text: string
  prompt_template: string
  prompt_rendered: string
  model: string
  temperature?: number | null
  started_at?: string | null
  completed_at?: string | null
  input_variables: AIInputVariable[]
  knowledge_refs: KnowledgeReference[]
  generated_text: string
  error_message: string
}

export type TraceDetail = FieldTraceDetail | ConditionTraceDetail | LoopTraceDetail | AITraceDetail
