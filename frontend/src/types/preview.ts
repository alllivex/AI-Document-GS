export interface PreviewNode {
  id?: string
  type: string
  text?: string
  trace_id?: string
  children?: PreviewNode[]
  [key: string]: unknown
}

export interface DocumentPreview {
  schema_version?: string
  doc_id?: string
  task_id?: string
  title?: string
  nodes?: PreviewNode[]
  [key: string]: unknown
}
