export function getTableDisplayName(item: {
  table_name?: string | null
  table_name_cn?: string | null
}) {
  return item.table_name_cn || item.table_name || '-'
}

export function getFieldDisplayName(item: {
  field_name?: string | null
  field_name_cn?: string | null
}) {
  return item.field_name_cn || item.field_name || '-'
}

export function getTemplateVarDisplayName(item: {
  original_var_path?: string | null
  var_path?: string | null
  canonical_var_path?: string | null
}) {
  return item.original_var_path || item.var_path || item.canonical_var_path || '-'
}
