export interface TraceItem {
  trace_id: string
  doc_id?: string
  task_id?: string
  table_name?: string
  table_name_cn?: string
  field_name?: string
  field_name_cn?: string
  excel_row_number?: number
  raw_value?: unknown
  display_value?: string
  [key: string]: unknown
}
