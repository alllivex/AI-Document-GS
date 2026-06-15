import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import vm from 'node:vm'
import ts from 'typescript'

const root = process.cwd()

function loadTsModule(relativePath) {
  const filename = path.join(root, relativePath)
  const source = fs.readFileSync(filename, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
    fileName: filename,
  }).outputText
  const module = { exports: {} }
  vm.runInNewContext(output, { exports: module.exports, module }, { filename })
  return module.exports
}

const {
  getFieldDisplayName,
  getTableDisplayName,
  getTemplateVarDisplayName,
} = loadTsModule('src/utils/displayName.ts')

assert.equal(getTableDisplayName({ table_name: 'branch_main', table_name_cn: '支行主表' }), '支行主表')
assert.equal(getTableDisplayName({ table_name: 'branch_main' }), 'branch_main')

assert.equal(getFieldDisplayName({ field_name: 'branch_name', field_name_cn: '支行名称' }), '支行名称')
assert.equal(getFieldDisplayName({ field_name: 'branch_name' }), 'branch_name')

assert.equal(
  getTemplateVarDisplayName({
    original_var_path: '支行表.支行名称',
    var_path: 'branch_main.branch_name',
    canonical_var_path: 'branch_main.branch_name',
  }),
  '支行表.支行名称',
)
assert.equal(
  getTemplateVarDisplayName({
    var_path: 'branch_main.branch_name',
    canonical_var_path: 'branch_main.branch_name',
  }),
  'branch_main.branch_name',
)
assert.equal(
  getTemplateVarDisplayName({
    canonical_var_path: 'branch_main.branch_name',
  }),
  'branch_main.branch_name',
)

const fieldPanel = fs.readFileSync(path.join(root, 'src/components/FieldTracePanel.vue'), 'utf8')
assert.match(fieldPanel, /getTableDisplayName\(trace\)/)
assert.match(fieldPanel, /getFieldDisplayName\(trace\)/)
assert.match(fieldPanel, /getTemplateVarDisplayName\(trace\)/)
assert.doesNotMatch(fieldPanel, /`\$\{[^`]+?（\$\{/)
assert.match(fieldPanel, /系统变量路径/)
assert.match(fieldPanel, /英文表名/)
assert.match(fieldPanel, /英文字段名/)

const sourceTable = fs.readFileSync(path.join(root, 'src/components/SourceRecordVerticalTable.vue'), 'utf8')
assert.match(sourceTable, /getFieldDisplayName\(row\)/)
assert.match(sourceTable, /trace-highlight-row/)
assert.doesNotMatch(sourceTable, /`\$\{[^`]+?（\$\{/)

assert.match(sourceTable, /data-source-highlight-target/)
assert.match(sourceTable, /source-highlight-focus/)

const previewRenderer = fs.readFileSync(path.join(root, 'src/components/PreviewRenderer.vue'), 'utf8')
assert.match(previewRenderer, /suppressAutoScrollTraceId/)
assert.match(previewRenderer, /selectTraceFromPreview/)

const traceDetailPanel = fs.readFileSync(path.join(root, 'src/components/TraceDetailPanel.vue'), 'utf8')
assert.match(traceDetailPanel, /data-source-highlight-target/)
assert.match(traceDetailPanel, /getBoundingClientRect/)
assert.match(traceDetailPanel, /panel\.scrollTo/)

console.log('display name and trace panel checks passed')
