# AGENTS.md

## 项目定义

本项目是一个 AI 智能文档生成系统：基于 Excel 业务数据和 Word 模板，批量生成干净 Word 文档，并在 Web 界面提供可视化数据溯源；本项目不是在线 Word 编辑器，也不是完整审核流系统。

## 边界

-   只生成干净 Word 文档，不在 Word 中写溯源批注
-   溯源审核在 Web 界面完成
-   不实现在线编辑 Word，编辑由用户下载到本地完成
-   MVP 不实现驳回、备注、复核、多人协同审核
-   MVP 不实现 RAG 知识库、复杂权限、模板在线编辑器

## 技术栈（固定，不可引入其他依赖）

以下为已选型，开发时不可自行引入新依赖。

后端固定技术栈：

-   Python 3.12
-   FastAPI
-   Uvicorn
-   Pydantic
-   pandas
-   openpyxl
-   docxtpl
-   python-docx
-   lxml
-   Jinja2
-   SQLite，使用 Python 标准库 sqlite3
-   OpenAI SDK，用于调用 DeepSeek OpenAI-compatible API
-   tenacity，用于 AI 调用重试
-   python-multipart，用于 FastAPI 文件上传
-   pytest，用于测试

前端固定技术栈：

-   Vue 3
-   TypeScript
-   Vite
-   Element Plus
-   Axios
-   Vue Router
-   Pinia，可选，仅用于必要的前端状态管理

禁止引入：

-   Handsontable
-   ONLYOFFICE
-   LibreOffice 服务端转换
-   Celery / Redis
-   PostgreSQL
-   LangChain
-   LlamaIndex
-   任意 RAG 框架
-   任意 Word 在线编辑 SDK

## 目录结构

    project_root/
    ├── AGENTS.md
    ├── README.md
    ├── backend/
    │   ├── requirements.txt
    │   ├── pyproject.toml
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── api/
    │   │   │   ├── health.py
    │   │   │   ├── templates.py
    │   │   │   ├── tasks.py
    │   │   │   ├── documents.py
    │   │   │   └── trace.py
    │   │   ├── core/
    │   │   │   ├── config.py
    │   │   │   ├── logging.py
    │   │   │   ├── errors.py
    │   │   │   └── response.py
    │   │   ├── db/
    │   │   │   ├── connection.py
    │   │   │   ├── schema.sql
    │   │   │   ├── init_db.py
    │   │   │   └── repositories/
    │   │   │       ├── template_repository.py
    │   │   │       ├── task_repository.py
    │   │   │       ├── document_repository.py
    │   │   │       ├── uploaded_file_repository.py
    │   │   │       ├── validation_repository.py
    │   │   │       └── log_repository.py
    │   │   ├── engine/
    │   │   │   ├── schema_loader.py
    │   │   │   ├── template_relation_loader.py
    │   │   │   ├── config_sync.py
    │   │   │   ├── template_requirement_service.py
    │   │   │   ├── data_loader.py
    │   │   │   ├── excel_utils.py
    │   │   │   ├── template_parser.py
    │   │   │   ├── validator.py
    │   │   │   ├── validation_report_writer.py
    │   │   │   ├── context_builder.py
    │   │   │   ├── trace_map.py
    │   │   │   ├── value_formatter.py
    │   │   │   ├── docx_renderer.py
    │   │   │   ├── ai_prompt_loader.py
    │   │   │   ├── ai_client.py
    │   │   │   ├── ai_generator.py
    │   │   │   ├── ai_block_applier.py
    │   │   │   ├── docx_finalizer.py
    │   │   │   ├── trace_builder.py
    │   │   │   ├── preview_builder.py
    │   │   │   ├── docx_preview_parser.py
    │   │   │   └── generation_runner.py
    │   │   ├── models/
    │   │   │   ├── common.py
    │   │   │   ├── enums.py
    │   │   │   ├── template_models.py
    │   │   │   ├── task_models.py
    │   │   │   ├── file_models.py
    │   │   │   ├── validation_models.py
    │   │   │   ├── trace_models.py
    │   │   │   ├── preview_models.py
    │   │   │   └── api_models.py
    │   │   ├── services/
    │   │   │   ├── task_service.py
    │   │   │   └── generation_service.py
    │   │   └── storage/
    │   │       ├── paths.py
    │   │       ├── file_manager.py
    │   │       ├── safe_filename.py
    │   │       └── zip_manager.py
    │   └── tests/
    │       ├── fixtures/
    │       ├── test_schema_loader.py
    │       ├── test_data_loader.py
    │       ├── test_validator.py
    │       ├── test_context_builder.py
    │       ├── test_docx_renderer.py
    │       ├── test_trace_preview_builder.py
    │       ├── test_generation_runner.py
    │       └── test_api_e2e.py
    ├── frontend/
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    │       ├── api/
    │       │   ├── http.ts
    │       │   ├── templates.ts
    │       │   ├── tasks.ts
    │       │   ├── documents.ts
    │       │   └── trace.ts
    │       ├── types/
    │       │   ├── api.ts
    │       │   ├── task.ts
    │       │   ├── template.ts
    │       │   ├── trace.ts
    │       │   ├── preview.ts
    │       │   └── validation.ts
    │       ├── views/
    │       │   ├── TaskListView.vue
    │       │   ├── TaskCreateView.vue
    │       │   ├── TaskResultView.vue
    │       │   └── DocumentTraceView.vue
    │       └── components/
    │           ├── TemplateSelector.vue
    │           ├── RequiredTableUploadList.vue
    │           ├── ValidationReportPanel.vue
    │           ├── OutputDocumentList.vue
    │           ├── PreviewRenderer.vue
    │           ├── TraceDetailPanel.vue
    │           ├── SourceRowTable.vue
    │           └── DocumentNavBar.vue
    ├── config/
    │   ├── entity_schema.xlsx
    │   ├── template_relation.xlsx
    │   └── db.sqlite
    ├── templates/
    │   └── *.docx
    ├── tasks/
    │   └── {task_id}/
    │       ├── meta.json
    │       ├── data/
    │       │   └── {table_name}.xlsx
    │       ├── validation/
    │       │   └── validation_report.json
    │       ├── output/
    │       │   ├── {template_name}_{primary_key_value}.docx
    │       │   ├── {template_name}_{primary_key_value}.trace.json
    │       │   └── {template_name}_{primary_key_value}.preview.json
    │       └── logs/
    │           └── generation.log
    └── temp/
        └── {task_id}/

## 核心数据流

1.  用户创建任务，选择模板，系统根据 template_relation 解析依赖表。
2.  用户上传 Excel，文件保存到 `tasks/{task_id}/data/{table_name}.xlsx`。
3.  系统执行模板、Schema、Excel字段、主键、AI Block 的生成前校验。
4.  系统按主表每一行构建 context 和 TraceMap，使用 docxtpl 渲染 Word，并可调用 DeepSeek 替换 AI 段落。
5.  系统输出干净 docx、`.trace.json`、`.preview.json`，Web 读取 preview 和 trace 展示溯源，用户下载 Word。

## 不可违背的规则

-   生成的 docx 绝不包含溯源批注

```{=html}
<!-- -->
```
-   所有业务数据必须存储在 `tasks/{task_id}/data/` 下

```{=html}
<!-- -->
```
-   模板变量必须使用 `{table_name}.{field_name}`，禁止恢复 `data.field_name`

```{=html}
<!-- -->
```
-   Web 预览必须基于 `.preview.json`，不要让前端直接解析 docx

```{=html}
<!-- -->
```
-   不要参考 `rag_*.py`、`smart_marking_system.py`、`fix_*.py`、`patch_*.py` 等旧文件

## 禁止事项

-   不要从 `word_gen_system_demo_with_marking.ipynb` 直接复制整段代码，只能按模块重构可用逻辑
-   不要在代码中添加任何 Word 批注溯源相关逻辑
-   不要实现审核通过、驳回、备注、复核、`.review.json` 写入
-   不要引入 RAG、知识库检索、智能分析引擎
-   不要把任务数据、输出文件、临时文件写到项目约定目录之外

## 可参考旧代码

允许参考的旧代码能力：

-   `load_entity_schema(schema_xlsx)`
-   `load_template_relation(relation_xlsx)`
-   `load_data_tables(data_dir, table_names)`
-   `build_translation_maps(schema_df)`，仅用于中文展示，不用于模板变量翻译
-   `TraceItem`，需按新契约扩展
-   `format_display_value(v)`
-   `build_report_contexts()`
-   `render_docx_template(template_docx, context, output_docx)`
-   `load_ai_prompts_from_template(template_docx)`
-   `render_prompt(prompt_tpl, context)`
-   `DeepSeekClient`
-   `get_ai_block_markers_for_template(template_path)`
-   `run_smart_document_generation(...)` 的流程思路

禁止参考的旧代码能力：

-   智能标记系统
-   Word 溯源批注
-   RAG 知识库
-   智能分析引擎
-   `_1.py`
-   `fix_*.py`
-   `patch_*.py`

## 当需要更多细节时

技术选型：

-   查看 `AI``智能文档生成系统``_MVP_PRD.md`
-   查看 `功能模块拆解与开发任务清单``.md`
-   查看本文件的"技术栈（固定，不可引入其他依赖）"

API 契约：

-   查看 `数据与接口契约文档``.md`
-   REST API 必须遵守统一响应结构：`success`、`data`、`error`、`request_id`、`timestamp`
-   文件下载接口除外，成功时返回文件流，失败时返回 JSON 错误

验收标准：

-   查看 `功能模块拆解与开发任务清单``.md`
-   每个模块必须满足对应的 3-5 条可测试验收标准
-   第一里程碑必须跑通：创建任务、上传 Excel、校验、生成、预览溯源、下载 Word、批量 ZIP

## 编码风格约定

Python：

-   函数使用 `snake_case`
-   类使用 `PascalCase`
-   常量使用 `UPPER_SNAKE_CASE`
-   必须添加 Type Hints
-   API 入参和出参优先使用 Pydantic Model
-   不在 API 路由函数中写复杂业务逻辑
-   复杂业务逻辑放入 `engine/` 或 `services/`
-   文件路径处理统一通过 `storage/paths.py` 和 `storage/file_manager.py`
-   异常统一通过 FastAPI 全局 exception handler 处理

Vue 3：

-   使用 Composition API
-   组件命名使用 `PascalCase`
-   API 调用集中放在 `src/api/`
-   类型定义集中放在 `src/types/`
-   页面组件放在 `src/views/`
-   通用组件放在 `src/components/`
-   不在组件中硬编码后端路径
-   不直接访问文件系统，只通过 REST API 获取数据和下载文件

错误处理：

-   FastAPI 必须配置全局异常 handler
-   所有 JSON 错误响应使用统一结构
-   业务错误必须有稳定错误码
-   常见错误码包括：`BAD_REQUEST`、`TASK_NOT_FOUND`、`TEMPLATE_NOT_FOUND`、`DOCUMENT_NOT_FOUND`、`TRACE_NOT_FOUND`、`FILE_NOT_FOUND`、`VALIDATION_FAILED`、`TASK_STATUS_INVALID`、`UPLOAD_FILE_INVALID`、`GENERATION_FAILED`、`INTERNAL_ERROR`

## 模板变量规则

-   所有模板变量统一使用英文表名和英文字段名
-   正确示例：`{{ customer_info.customer_name }}`
-   正确示例：`{{ loan_summary.loan_balance }}`
-   错误示例：`{{ data.customer_name }}`
-   错误示例：`{{ ``客户信息表``.``客户名称`` }}`
-   `role=main` 只表示批量生成驱动表
-   主表在模板中仍使用真实表名，不使用别名
-   一对一辅表在 context 中是 dict
-   一对多辅表在 context 中是 list
-   Word 表格循环使用 docxtpl 的 `{%tr for item in table_name %}` 语法

## 输出文件规则

-   单份 Word：`tasks/{task_id}/output/{safe_template_name}_{safe_primary_key_value}.docx`
-   溯源文件：`tasks/{task_id}/output/{safe_template_name}_{safe_primary_key_value}.trace.json`
-   预览文件：`tasks/{task_id}/output/{safe_template_name}_{safe_primary_key_value}.preview.json`
-   校验报告：`tasks/{task_id}/validation/validation_report.json`
-   任务元数据：`tasks/{task_id}/meta.json`
-   日志文件：`tasks/{task_id}/logs/generation.log`
-   ZIP 下载临时文件：`temp/{task_id}/{task_id}_outputs.zip`

## 第一里程碑目标

第一里程碑完成后，系统必须能完成以下闭环：

1.  启动 FastAPI 后端服务
2.  启动 Vue 前端服务
3.  选择一个 Word 模板
4.  创建一个生成任务
5.  上传主表和辅表 Excel
6.  执行生成前校验
7.  按主表行数批量生成 Word
8.  为每份 Word 生成 `.trace.json`
9.  为每份 Word 生成 `.preview.json`
10. 在 Web 页面查看文档结构化预览
11. 点击字段查看来源 Excel 文件、表、字段、行号、原始值、展示值
12. 下载单个 Word
13. 批量下载 ZIP
14. 本地 Word/WPS 可正常打开生成文件
15. 生成文件不包含任何系统标记或溯源批注
