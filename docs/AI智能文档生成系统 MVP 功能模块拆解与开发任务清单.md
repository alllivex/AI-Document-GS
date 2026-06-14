# AI智能文档生成系统 MVP 功能模块拆解与开发任务清单

> 目标：用于指导 Codex 按模块、按依赖顺序逐步开发。\
> 原则：不要一次性把整个项目丢给Codex生成；应逐模块开发、测试、提交。\
> MVP边界：Excel上传、配置加载、模板校验、批量生成Word、AI段落生成、trace/preview生成、Web溯源查看、Word/ZIP下载。\
> 非MVP边界：不做审核流、不做驳回/备注、不做在线Word编辑、不做RAG、不做Word内溯源批注、不做复杂权限。

# 一、总体开发顺序

## 1.1 推荐模块依赖顺序

    M01 项目骨架与配置
      ↓
    M02 数据模型与类型定义
      ↓
    M03 文件路径与任务工作区管理
      ↓
    M04 SQLite数据库初始化与Repository
      ↓
    M05 配置Excel加载与同步
      ↓
    M06 模板依赖解析服务
      ↓
    M07 任务创建与文件上传
      ↓
    M08 Excel业务数据加载
      ↓
    M09 生成前校验引擎
      ↓
    M10 Context与TraceMap构建
      ↓
    M11 Word模板渲染
      ↓
    M12 AI Prompt提取与AI生成
      ↓
    M13 AI段落替换与最终docx生成
      ↓
    M14 trace.json与preview.json生成
      ↓
    M15 批量生成编排器
      ↓
    M16 FastAPI接口层
      ↓
    M17 前端API客户端与类型
      ↓
    M18 前端任务管理页面
      ↓
    M19 前端文档溯源预览页面
      ↓
    M20 下载与ZIP打包
      ↓
    M21 测试样例与端到端验收

## 1.2 第一里程碑 MVP 范围

第一里程碑建议包含：

    M01 项目骨架与配置
    M02 数据模型与类型定义
    M03 文件路径与任务工作区管理
    M04 SQLite数据库初始化与Repository
    M05 配置Excel加载与同步
    M06 模板依赖解析服务
    M07 任务创建与文件上传
    M08 Excel业务数据加载
    M09 生成前校验引擎
    M10 Context与TraceMap构建
    M11 Word模板渲染
    M12 AI Prompt提取与AI生成
    M13 AI段落替换与最终docx生成
    M14 trace.json与preview.json生成
    M15 批量生成编排器
    M16 FastAPI接口层
    M18 前端任务管理页面
    M19 前端文档溯源预览页面
    M20 下载与ZIP打包
    M21 测试样例与端到端验收

可后置但不影响第一版演示的模块：

    模板上传管理
    模板版本管理
    用户权限
    复杂日志检索
    自定义文件名规则
    中文变量兼容
    RAG知识库
    审核流
    在线Word编辑

# 二、模块拆解清单

# M01 项目骨架与配置模块

## 一句话描述

建立标准FastAPI + Vue + Engine分层项目结构，统一配置文件、环境变量、日志和启动入口。

## 涉及文件

    backend/
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── logging.py
    │   │   ├── errors.py
    │   │   └── response.py
    │   ├── api/
    │   ├── db/
    │   ├── engine/
    │   ├── models/
    │   └── storage/
    ├── requirements.txt
    ├── pyproject.toml
    └── README.md

    frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/

## 输入

    class SettingsInput(BaseModel):
        env_file: str = ".env"

环境变量：

    APP_ENV=dev
    PROJECT_ROOT=.
    DATABASE_URL=sqlite:///config/db.sqlite
    DEEPSEEK_API_KEY=xxx
    DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
    DEEPSEEK_MODEL=deepseek-chat

## 输出

    class AppSettings(BaseModel):
        project_root: Path
        database_path: Path
        config_dir: Path
        templates_dir: Path
        tasks_dir: Path
        temp_dir: Path
        deepseek_api_key: str | None
        deepseek_base_url: str
        deepseek_model: str

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  执行 `python -m app.main` 或 `uvicorn app.main:app --reload` 后服务可启动。
2.  访问 `GET /health` 返回 `{"status":"ok"}`。
3.  未配置 `DEEPSEEK_API_KEY` 时服务仍可启动，但AI功能显示不可用。
4.  `config/`、`templates/`、`tasks/`、`temp/` 目录不存在时可自动创建。
5.  所有路径均以 `PROJECT_ROOT` 为基准，不使用硬编码绝对路径。

## 复杂度标记

低复杂度。不需要伪代码。

# M02 数据模型与类型定义模块

## 一句话描述

定义后端Pydantic模型、枚举、通用API响应、trace、preview、task、validation等核心数据结构。

## 涉及文件

    backend/app/models/
    ├── common.py
    ├── enums.py
    ├── template_models.py
    ├── task_models.py
    ├── file_models.py
    ├── validation_models.py
    ├── trace_models.py
    ├── preview_models.py
    └── api_models.py

## 输入

无外部输入。根据《数据与接口契约文档》编码。

## 输出

核心类型：

    class ApiResponse[T](BaseModel):
        success: bool
        data: T | None = None
        error: ApiErrorDetail | None = None
        request_id: str
        timestamp: datetime

    class TraceItem(BaseModel):
        trace_id: str
        var_path: str
        table_name: str
        table_name_cn: str
        field_name: str
        field_name_cn: str
        source_file: str
        source_file_path: str
        pk_field: str
        pk_value: str
        row_index: int
        excel_row_number: int
        column_index: int | None
        excel_column_letter: str | None
        raw_value: str | int | float | bool | None
        display_value: str
        value_type: DataType
        display_format: str
        occurrence_index: int
        source_relation_type: RelationType
        created_at: datetime

## 可参考旧代码

旧代码中的 `TraceItem` 可作为字段语义参考，但需要按新契约扩展字段。

## 验收标准

1.  所有模型可以被 `pytest` 正常导入。
2.  `TraceItem` 能通过Pydantic校验合法样例。
3.  非法枚举值会触发校验错误。
4.  所有API响应统一使用 `ApiResponse` 或等价包装。
5.  模型字段命名与接口契约保持一致，禁止出现 `data.xxx` 主表别名设计。

## 复杂度标记

低复杂度。不需要伪代码。

# M03 文件路径与任务工作区管理模块

## 一句话描述

统一管理任务目录、上传目录、输出目录、校验目录、日志目录、临时目录，防止路径混乱和路径穿越。

## 涉及文件

    backend/app/storage/
    ├── paths.py
    ├── file_manager.py
    └── safe_filename.py

## 输入

    class CreateTaskWorkspaceInput(BaseModel):
        task_id: str

    class SaveUploadInput(BaseModel):
        task_id: str
        table_name: str
        original_filename: str
        file_bytes: bytes

## 输出

    class TaskWorkspace(BaseModel):
        task_id: str
        task_dir: Path
        data_dir: Path
        output_dir: Path
        validation_dir: Path
        logs_dir: Path
        temp_dir: Path
        meta_path: Path

    class StoredFileInfo(BaseModel):
        table_name: str
        original_filename: str
        stored_filename: str
        file_path: Path
        file_size: int

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  输入 `task_id="task_20260613_153000_a1b2c3"` 后能创建完整目录结构。
2.  上传 `customer_info.xlsx` 后保存为 `tasks/{task_id}/data/customer_info.xlsx`。
3.  文件名包含 `\ / : * ? " < > |` 时会被安全替换为 `_`。
4.  传入 `../evil.xlsx` 不能写入项目根目录之外。
5.  输出文件名超过120字符时自动截断并附加短hash。

## 复杂度标记

中低复杂度。建议给Codex明确路径规则。

# M04 SQLite数据库初始化与Repository模块

## 一句话描述

创建SQLite表结构，并封装templates、tasks、documents、uploaded_files、logs、validation_reports的数据库访问。

## 涉及文件

    backend/app/db/
    ├── connection.py
    ├── schema.sql
    ├── init_db.py
    ├── repositories/
    │   ├── template_repository.py
    │   ├── task_repository.py
    │   ├── document_repository.py
    │   ├── uploaded_file_repository.py
    │   ├── validation_repository.py
    │   └── log_repository.py

## 输入

    class DatabaseInitInput(BaseModel):
        database_path: Path

    class CreateTaskRecordInput(BaseModel):
        task_id: str
        task_name: str
        template_id: int
        template_name: str
        ai_enabled: bool
        main_table: str
        primary_key_field: str
        task_dir: str

## 输出

    class TaskRecord(BaseModel):
        task_id: str
        task_name: str
        template_id: int
        template_name: str
        status: TaskStatus
        ai_enabled: bool
        main_table: str
        primary_key_field: str
        total_rows: int
        success_count: int
        failed_count: int
        created_at: datetime
        updated_at: datetime

## 可参考旧代码

无。旧Notebook没有正式数据库层。

## 验收标准

1.  执行初始化脚本后，SQLite中存在所有契约定义的表。
2.  `tasks` 表可成功插入、更新状态、按ID查询。
3.  `documents` 表可按 `task_id` 查询文档列表。
4.  所有Repository方法不直接拼接未清洗SQL。
5.  数据库文件不存在时可自动初始化。

## 复杂度标记

中复杂度。建议先只做同步方法，不要一开始引入复杂ORM。

# M05 配置Excel加载与同步模块

## 一句话描述

读取 `entity_schema.xlsx` 和 `template_relation.xlsx`，解析字段字典与模板依赖关系，并同步到SQLite。

## 涉及文件

    backend/app/engine/
    ├── schema_loader.py
    ├── template_relation_loader.py
    └── config_sync.py

## 输入

    class LoadSchemaInput(BaseModel):
        schema_xlsx: Path

    class LoadTemplateRelationInput(BaseModel):
        relation_xlsx: Path

## 输出

    class FieldDefinition(BaseModel):
        table_name: str
        table_name_cn: str
        field_name: str
        field_name_cn: str
        data_type: DataType
        is_primary_key: bool
        required: bool
        display_format: str
        description: str

    class TemplateRelationDefinition(BaseModel):
        template_id: int
        template_name: str
        template_file: str
        table_name: str
        table_name_cn: str
        role: Literal["main", "aux"]
        relation_type: RelationType
        main_join_key: str
        table_join_key: str
        required: bool
        description: str

## 可参考旧代码

可参考：

    load_entity_schema(schema_xlsx)
    load_template_relation(relation_xlsx)
    build_translation_maps(schema_df)
    translate_table_name()
    translate_field_name()

但MVP不做中文变量兼容，所以 `build_translation_maps` 可暂时只用于中文展示，不用于模板变量翻译。

## 验收标准

1.  正确读取 `entity_schema.xlsx` 并返回字段列表。
2.  正确读取 `template_relation.xlsx` 并返回模板依赖列表。
3.  同一表有多个主键时抛出配置错误。
4.  同一模板没有主表或存在多个主表时抛出配置错误。
5.  同步到SQLite后，`GET /api/templates` 可读到模板信息。

## 复杂度标记

中复杂度。配置校验细节较多。

# M06 模板依赖解析服务

## 一句话描述

根据 `template_id` 聚合模板、主表、辅表、字段、关联键，形成前端新建任务和后端生成任务都能使用的模板需求对象。

## 涉及文件

    backend/app/engine/
    └── template_requirement_service.py

    backend/app/models/
    └── template_models.py

## 输入

    class GetTemplateRequirementsInput(BaseModel):
        template_id: int

## 输出

    class TemplateRequirements(BaseModel):
        template_id: int
        template_name: str
        template_file: str
        template_path: str
        main_table: str
        primary_key_field: str
        required_tables: list[RequiredTable]

## 可参考旧代码

可参考旧代码中 `load_template_relation` 的数据结构和"按模板ID选出依赖表"的逻辑。

## 验收标准

1.  输入有效 `template_id`，返回主表、辅表、字段清单。
2.  主表能正确识别主键字段。
3.  辅表能返回 `relation_type`、`main_join_key`、`table_join_key`。
4.  输入不存在的 `template_id` 返回明确错误。
5.  模板需求对象可直接用于前端展示上传文件要求。

## 复杂度标记

中低复杂度。不需要复杂算法。

# M07 任务创建与文件上传模块

## 一句话描述

提供创建任务、初始化任务目录、上传Excel文件、记录上传文件元数据的能力。

## 涉及文件

    backend/app/services/
    └── task_service.py

    backend/app/storage/
    ├── file_manager.py
    └── paths.py

    backend/app/api/
    └── tasks.py

## 输入

    class CreateTaskRequest(BaseModel):
        task_name: str
        template_id: int
        ai_enabled: bool = True

    class UploadTaskFileRequest:
        task_id: str
        table_name: str
        file: UploadFile

## 输出

    class CreateTaskResponse(BaseModel):
        task_id: str
        task_name: str
        template_id: int
        template_name: str
        status: TaskStatus
        task_dir: str
        required_tables: list[RequiredTable]
        created_at: datetime

    class UploadTaskFileResponse(BaseModel):
        task_id: str
        table_name: str
        original_filename: str
        stored_filename: str
        file_path: str
        file_size: int
        row_count: int
        column_count: int
        uploaded_at: datetime

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  创建任务后数据库 `tasks` 有记录，状态为 `created`。
2.  创建任务后本地存在 `tasks/{task_id}/meta.json`。
3.  上传文件后保存到 `tasks/{task_id}/data/{table_name}.xlsx`。
4.  上传非 `.xlsx` 文件返回 `UPLOAD_FILE_INVALID`。
5.  重复上传同一 `table_name` 时覆盖旧文件，并更新 `uploaded_files` 记录。

## 复杂度标记

中复杂度。需注意文件安全和任务状态。

# M08 Excel业务数据加载模块

## 一句话描述

从任务数据目录读取Excel业务表，转换为DataFrame，并保留字段、行号、列号等溯源所需信息。

## 涉及文件

    backend/app/engine/
    ├── data_loader.py
    └── excel_utils.py

## 输入

    class LoadDataTablesInput(BaseModel):
        data_dir: Path
        table_names: list[str]

## 输出

    class LoadedTable(BaseModel):
        table_name: str
        source_file: str
        source_file_path: str
        dataframe: Any  # pandas.DataFrame
        columns: list[str]
        row_count: int
        column_count: int
        column_index_map: dict[str, int]
        excel_column_letter_map: dict[str, str]

    class LoadedDataTables(BaseModel):
        tables: dict[str, LoadedTable]

## 可参考旧代码

可参考：

    load_data_tables(data_dir, table_names)

需要增强：

    column_index_map
    excel_column_letter_map
    source_file_path
    row_count
    column_count

## 验收标准

1.  给定 `customer_info.xlsx` 可读取为DataFrame。
2.  第一行识别为字段名。
3.  能返回字段到Excel列字母的映射，例如 `customer_name -> B`。
4.  文件不存在时返回明确错误。
5.  空Excel或无表头Excel返回明确错误。

## 复杂度标记

中低复杂度。

# M09 生成前校验引擎

## 一句话描述

在生成前检查模板配置、上传文件、Excel字段、主键、关联关系、模板变量和AI Block，输出validation_report.json。

## 涉及文件

    backend/app/engine/
    ├── validator.py
    ├── template_parser.py
    └── validation_report_writer.py

    backend/app/models/
    └── validation_models.py

## 输入

    class ValidateTaskInput(BaseModel):
        task_id: str
        template_requirements: TemplateRequirements
        loaded_tables: LoadedDataTables
        template_path: Path

## 输出

    class ValidationReport(BaseModel):
        schema_version: Literal["1.0"]
        task_id: str
        status: Literal["passed", "failed", "passed_with_warnings"]
        summary: ValidationSummary
        items: list[ValidationItem]
        created_at: datetime

## 可参考旧代码

可参考旧代码中配置加载、数据表加载、主键识别的逻辑。

不建议复用旧代码中复杂的条件表达式追踪，MVP只做模板变量存在性校验。

## 验收标准

1.  缺少主表Excel时返回 `missing_required_table` error。
2.  主表主键为空或重复时返回 error。
3.  模板引用不存在字段时返回 `missing_field` error。
4.  一对一辅表匹配多行时返回 error。
5.  校验通过时生成 `tasks/{task_id}/validation/validation_report.json`。

## 复杂度标记

高复杂度。必须给Codex伪代码。

## 伪代码

    def validate_task(task_id, requirements, loaded_tables, template_path):
        report = ValidationReport(task_id=task_id)

        # 1. 校验模板文件
        if not template_path.exists():
            report.add_error("template_file_missing")

        # 2. 校验依赖表文件
        for table_req in requirements.required_tables:
            if table_req.table_name not in loaded_tables.tables:
                if table_req.required:
                    report.add_error("missing_required_table")
                else:
                    report.add_warning("missing_optional_table")

        # 3. 校验字段
        for table_req in requirements.required_tables:
            table = loaded_tables.tables.get(table_req.table_name)
            if not table:
                continue

            schema_fields = get_schema_fields(table_req.table_name)
            for field in schema_fields:
                if field.required and field.field_name not in table.columns:
                    report.add_error("missing_required_field")

        # 4. 校验主表主键
        main_table = loaded_tables.tables[requirements.main_table]
        pk = requirements.primary_key_field

        if pk not in main_table.columns:
            report.add_error("missing_primary_key_field")
        else:
            if main_table.df[pk].isnull().any():
                report.add_error("empty_primary_key")
            if main_table.df[pk].duplicated().any():
                report.add_error("duplicated_primary_key")

        # 5. 校验辅表关联键
        for aux in requirements.aux_tables:
            table = loaded_tables.tables.get(aux.table_name)
            if not table:
                continue

            if aux.table_join_key not in table.columns:
                report.add_error("missing_aux_join_key")

            if aux.relation_type == "one_to_one":
                duplicated_keys = table.df[aux.table_join_key].duplicated()
                if duplicated_keys.any():
                    report.add_error("one_to_one_multiple_rows")

        # 6. 解析模板变量
        variables = extract_jinja_variables_from_docx(template_path)
        for var_path in variables:
            table_name, field_name = split_var_path(var_path)
            if table_name not in requirements.allowed_table_names:
                report.add_error("unknown_template_table")
            elif field_name not in schema_fields_of(table_name):
                report.add_error("unknown_template_field")

        # 7. 校验AI Block
        ai_markers = extract_ai_block_markers(template_path)
        ai_prompts = extract_comment_prompts(template_path)
        if len(ai_markers) != len(ai_prompts):
            report.add_warning("ai_block_prompt_mismatch")

        # 8. 汇总状态
        if report.error_count > 0:
            report.status = "failed"
        elif report.warning_count > 0:
            report.status = "passed_with_warnings"
        else:
            report.status = "passed"

        write_validation_report(task_id, report)
        return report

# M10 Context与TraceMap构建模块

## 一句话描述

按主表每一行构建单份文档的Jinja context，同时生成字段级TraceItem基础数据。

## 涉及文件

    backend/app/engine/
    ├── context_builder.py
    ├── trace_map.py
    └── value_formatter.py

## 输入

    class BuildContextsInput(BaseModel):
        task_id: str
        template_requirements: TemplateRequirements
        loaded_tables: LoadedDataTables

## 输出

    class ReportContextBundle(BaseModel):
        doc_id: str
        primary_key_value: str
        context: dict[str, Any]
        trace_map: dict[str, list[TraceItem]]
        source_rows: dict[str, Any]

其中：

    ReportContextList = list[ReportContextBundle]

## 可参考旧代码

重点参考：

    TraceItem
    format_display_value(v)
    build_report_contexts()

旧代码中这是最核心函数，应优先复用思路。

## 验收标准

1.  主表3行时输出3个 `ReportContextBundle`。
2.  context中主表使用真实表名，例如 `customer_info.customer_name`，禁止生成 `data.customer_name`。
3.  一对一辅表输出dict。
4.  一对多辅表输出list。
5.  每个进入context的字段都能在trace_map中找到对应TraceItem。

## 复杂度标记

高复杂度。必须给Codex伪代码。

## 伪代码

    def build_report_contexts(requirements, loaded_tables):
        main_req = requirements.main_table_req
        main_table = loaded_tables.tables[main_req.table_name]
        pk_field = requirements.primary_key_field

        bundles = []

        for row_index, main_row in main_table.df.iterrows():
            pk_value = str(main_row[pk_field])
            doc_id = generate_doc_id()

            context = {}
            trace_map = {}
            source_rows = {}

            # 1. 主表dict
            main_context = {}
            for field in main_table.columns:
                raw_value = main_row[field]
                display_value = format_display_value(raw_value, field_schema)
                main_context[field] = display_value

                var_path = f"{main_req.table_name}.{field}"
                trace_item = build_trace_item(
                    var_path=var_path,
                    table=main_table,
                    field=field,
                    raw_value=raw_value,
                    display_value=display_value,
                    pk_field=pk_field,
                    pk_value=pk_value,
                    row_index=row_index,
                    relation_type="main"
                )
                trace_map.setdefault(var_path, []).append(trace_item)

            context[main_req.table_name] = main_context
            source_rows[main_req.table_name] = main_row.to_dict()

            # 2. 辅表
            for aux_req in requirements.aux_tables:
                aux_table = loaded_tables.tables[aux_req.table_name]
                matched_df = aux_table.df[
                    aux_table.df[aux_req.table_join_key].astype(str) == pk_value
                ]

                if aux_req.relation_type == "one_to_one":
                    if len(matched_df) == 0:
                        context[aux_req.table_name] = {}
                        continue

                    aux_row = matched_df.iloc[0]
                    aux_context = {}

                    for field in aux_table.columns:
                        raw_value = aux_row[field]
                        display_value = format_display_value(raw_value, field_schema)
                        aux_context[field] = display_value

                        var_path = f"{aux_req.table_name}.{field}"
                        trace_item = build_trace_item(...)
                        trace_map.setdefault(var_path, []).append(trace_item)

                    context[aux_req.table_name] = aux_context

                elif aux_req.relation_type == "one_to_many":
                    aux_list = []

                    for matched_row_index, aux_row in matched_df.iterrows():
                        item_context = {}

                        for field in aux_table.columns:
                            raw_value = aux_row[field]
                            display_value = format_display_value(raw_value, field_schema)
                            item_context[field] = display_value

                            var_path = f"{aux_req.table_name}.{field}"
                            trace_item = build_trace_item(
                                occurrence_index=len(aux_list)
                            )
                            trace_map.setdefault(var_path, []).append(trace_item)

                        aux_list.append(item_context)

                    context[aux_req.table_name] = aux_list

            bundles.append(
                ReportContextBundle(
                    doc_id=doc_id,
                    primary_key_value=pk_value,
                    context=context,
                    trace_map=trace_map,
                    source_rows=source_rows
                )
            )

        return bundles

# M11 Word模板渲染模块

## 一句话描述

使用docxtpl将Word模板中的变量、条件判断、表格循环渲染为中间docx。

## 涉及文件

    backend/app/engine/
    └── docx_renderer.py

## 输入

    class RenderDocxInput(BaseModel):
        template_path: Path
        context: dict[str, Any]
        output_path: Path

## 输出

    class RenderDocxResult(BaseModel):
        output_path: Path
        success: bool
        error_message: str = ""

## 可参考旧代码

可直接参考：

    render_docx_template(template_docx, context, output_docx)

## 验收标准

1.  模板中 `{{ customer_info.customer_name }}` 能正确替换。
2.  `{% if %}` 条件判断能正确渲染。
3.  `{%tr for item in collateral_info %}` 表格循环能正确生成多行。
4.  渲染后的docx可被Word或WPS打开。
5.  渲染失败时返回明确错误，不生成损坏文件。

## 复杂度标记

中复杂度。docxtpl表格循环要重点测试。

# M12 AI Prompt提取与AI生成模块

## 一句话描述

从Word批注读取AI prompt，渲染prompt变量，调用DeepSeek生成AI段落文本。

## 涉及文件

    backend/app/engine/
    ├── ai_prompt_loader.py
    ├── ai_client.py
    └── ai_generator.py

## 输入

    class AIPromptLoadInput(BaseModel):
        template_path: Path

    class AIGenerateInput(BaseModel):
        block_id: str
        prompt_template: str
        context: dict[str, Any]
        model: str = "deepseek-chat"

## 输出

    class AIPromptDefinition(BaseModel):
        block_id: str
        marker: str
        prompt_template: str
        comment_id: str | None

    class AIGenerateResult(BaseModel):
        block_id: str
        status: Literal["success", "failed"]
        prompt_template: str
        prompt_rendered: str
        generated_text: str
        model: str
        error_message: str
        started_at: datetime | None
        completed_at: datetime | None

## 可参考旧代码

可参考：

    load_ai_prompts_from_template(template_docx)
    render_prompt(prompt_tpl, context)
    DeepSeekClient
    get_ai_block_markers_for_template(template_path)

## 验收标准

1.  能从模板批注中提取 `prompt="..."`。
2.  能识别 `§AIBLOCK0§`、`§AIBLOCK1§`。
3.  prompt中的 `{{ customer_info.customer_name }}` 能被context正确渲染。
4.  未配置API Key时返回AI不可用错误，但不导致系统崩溃。
5.  AI调用失败时返回 `status="failed"` 和明确 `error_message`。

## 复杂度标记

中高复杂度。批注XML解析和AI异常处理需要小心。

# M13 AI段落替换与最终docx生成模块

## 一句话描述

在中间docx中定位 `§AIBLOCKn§` 段落，并用AI生成内容替换，输出最终干净docx。

## 涉及文件

    backend/app/engine/
    ├── ai_block_applier.py
    └── docx_finalizer.py

## 输入

    class ApplyAIBlocksInput(BaseModel):
        rendered_docx_path: Path
        output_docx_path: Path
        ai_results: list[AIGenerateResult]
        ai_enabled: bool

## 输出

    class ApplyAIBlocksResult(BaseModel):
        output_docx_path: Path
        ai_status: Literal["not_used", "success", "partial_failed", "failed"]
        ai_blocks: list[AIBlockTrace]
        error_message: str = ""

## 可参考旧代码

选择性参考：

    finalize_rendered_document() 中的 apply_ai_by_markers() 部分

不得复用：

    Word溯源批注相关逻辑
    annotate_values_in_document 系列函数

## 验收标准

1.  `§AIBLOCK0§` 能被AI生成文本替换。
2.  最终docx中不存在 `§AIBLOCK` 字样。
3.  AI失败时删除AI标记并保留原段落文本。
4.  不向Word写入任何溯源批注。
5.  输出docx可被Word或WPS正常打开。

## 复杂度标记

高复杂度。建议给Codex伪代码。

## 伪代码

    def apply_ai_blocks(rendered_docx_path, output_docx_path, ai_results, ai_enabled):
        doc = Document(rendered_docx_path)

        ai_result_map = {
            result.marker: result
            for result in ai_results
        }

        for paragraph in doc.paragraphs:
            text = paragraph.text

            marker = find_ai_marker(text)
            if not marker:
                continue

            result = ai_result_map.get(marker)

            if not ai_enabled:
                replacement = text.replace(marker, "").strip()

            elif result and result.status == "success":
                replacement = result.generated_text.strip()

            else:
                # AI失败，保留原文但去掉marker
                replacement = text.replace(marker, "").strip()

            clear_paragraph_runs(paragraph)
            paragraph.add_run(replacement)

        # 表格中的AI段落如需要，也遍历table cells
        for table in doc.tables:
            for cell in table._cells:
                for paragraph in cell.paragraphs:
                    repeat_same_logic()

        doc.save(output_docx_path)

        return ApplyAIBlocksResult(...)

# M14 trace.json与preview.json生成模块

## 一句话描述

根据context、trace_map、最终docx或渲染事件，生成Web溯源查看所需的trace.json和preview.json。

## 涉及文件

    backend/app/engine/
    ├── trace_builder.py
    ├── preview_builder.py
    └── docx_preview_parser.py

## 输入

    class BuildTracePreviewInput(BaseModel):
        task_id: str
        doc_id: str
        template_id: int
        template_name: str
        template_file: str
        output_file: str
        output_path: Path
        main_table: str
        main_table_cn: str
        primary_key_field: str
        primary_key_value: str
        trace_map: dict[str, list[TraceItem]]
        ai_blocks: list[AIBlockTrace]
        final_docx_path: Path

## 输出

    class BuildTracePreviewResult(BaseModel):
        trace_file_path: Path
        preview_file_path: Path
        trace_count: int
        ai_block_count: int

## 可参考旧代码

可参考旧代码中的 `TraceItem` 和 `build_report_contexts()` 的trace思路。

不可参考旧代码中的Word批注溯源。

## 验收标准

1.  每份docx生成一个同名 `.trace.json`。
2.  每份docx生成一个同名 `.preview.json`。
3.  preview中可溯源文本包含 `trace_id`。
4.  trace中的 `trace_id` 可在preview中被引用。
5.  点击preview中的trace_id后能找到来源文件、表、字段、行号、原始值和展示值。

## 复杂度标记

高复杂度。必须给Codex伪代码和降级策略。

## 重要实现说明

MVP不要追求完美定位Word中的所有run。建议第一版采用"结构化预览优先"策略：

1.  Word最终docx用于下载。
2.  Web预览不要求100%复刻Word排版。
3.  preview.json可以由"最终docx文本 + trace_map匹配"生成。
4.  如果同一个展示值重复出现，优先按变量出现顺序匹配。
5.  无法可靠匹配的文本仍展示，但不带trace_id。

## 伪代码

    def build_trace_and_preview(input):
        # 1. 生成trace.json
        trace_items = flatten_trace_map(input.trace_map)

        trace_file = TraceFile(
            doc_id=input.doc_id,
            task_id=input.task_id,
            template_id=input.template_id,
            template_name=input.template_name,
            output_file=input.output_file,
            main_table=input.main_table,
            primary_key_field=input.primary_key_field,
            primary_key_value=input.primary_key_value,
            trace_items=trace_items,
            ai_blocks=input.ai_blocks,
            statistics=...
        )

        write_json(trace_path, trace_file)

        # 2. 解析最终docx为段落和表格
        doc = Document(input.final_docx_path)
        blocks = []

        trace_queue_by_display_value = build_queue(trace_items)

        # 3. 段落预览
        for paragraph in doc.paragraphs:
            text = paragraph.text
            if not text.strip():
                continue

            runs = split_text_with_trace(text, trace_queue_by_display_value)
            blocks.append(PreviewParagraphBlock(runs=runs))

        # 4. 表格预览
        for table in doc.tables:
            headers, rows = parse_table_cells(table)
            attach_trace_to_cells(headers, trace_queue_by_display_value)
            attach_trace_to_cells(rows, trace_queue_by_display_value)
            blocks.append(PreviewTableBlock(headers=headers, rows=rows))

        preview_file = PreviewFile(
            doc_id=input.doc_id,
            task_id=input.task_id,
            title=input.output_file,
            primary_key_value=input.primary_key_value,
            blocks=blocks
        )

        write_json(preview_path, preview_file)

        return BuildTracePreviewResult(...)

# M15 批量生成编排器模块

## 一句话描述

串联配置、数据、校验、context、docxtpl、AI、trace、preview、数据库记录，完成一个任务的批量生成。

## 涉及文件

    backend/app/engine/
    └── generation_runner.py

    backend/app/services/
    └── generation_service.py

## 输入

    class GenerateTaskInput(BaseModel):
        task_id: str
        force: bool = False
        ai_enabled: bool = True

## 输出

    class GenerateTaskResult(BaseModel):
        task_id: str
        status: TaskStatus
        total_rows: int
        success_count: int
        failed_count: int
        document_ids: list[str]
        error_message: str = ""

## 可参考旧代码

重点参考：

    run_smart_document_generation(template_ids, ...)

但必须修改：

    去掉多模板复杂逻辑，MVP一次任务只处理一个template_id
    去掉Word溯源批注参数
    改为生成 trace.json + preview.json

## 验收标准

1.  主表3行时生成3份docx、3份trace、3份preview。
2.  单份文档失败不影响其他文档继续生成。
3.  数据库documents表记录每份输出文档。
4.  任务最终状态能正确更新为 `completed`、`partial_failed` 或 `failed`。
5.  生成日志写入 `generation_logs` 和 `tasks/{task_id}/logs/generation.log`。

## 复杂度标记

高复杂度。必须给Codex伪代码。

## 伪代码

    def generate_task(task_id, force=False, ai_enabled=True):
        task = task_repo.get(task_id)

        assert_task_status_can_generate(task, force)

        task_repo.update_status(task_id, "running")

        requirements = template_requirement_service.get(task.template_id)

        loaded_tables = data_loader.load(
            data_dir=workspace.data_dir,
            table_names=requirements.table_names
        )

        validation_report = validator.validate_task(...)
        if validation_report.status == "failed":
            task_repo.update_status(task_id, "validation_failed")
            return GenerateTaskResult(status="validation_failed")

        bundles = context_builder.build_report_contexts(...)

        success_count = 0
        failed_count = 0
        document_ids = []

        for bundle in bundles:
            try:
                output_paths = build_output_paths(bundle.primary_key_value)

                rendered_docx = temp_path(...)
                final_docx = output_paths.docx

                docx_renderer.render(
                    template_path=requirements.template_path,
                    context=bundle.context,
                    output_path=rendered_docx
                )

                ai_prompts = ai_prompt_loader.load(requirements.template_path)

                ai_results = []
                if ai_enabled:
                    for prompt in ai_prompts:
                        result = ai_generator.generate(prompt, bundle.context)
                        ai_results.append(result)

                finalizer.apply_ai_blocks(
                    rendered_docx_path=rendered_docx,
                    output_docx_path=final_docx,
                    ai_results=ai_results
                )

                trace_preview_result = trace_builder.build(...)

                document_repo.create(...)
                success_count += 1

            except Exception as e:
                failed_count += 1
                log_error(task_id, bundle.doc_id, e)
                continue

        final_status = decide_status(success_count, failed_count)
        task_repo.update_summary(...)

        return GenerateTaskResult(...)

# M16 FastAPI接口层模块

## 一句话描述

把后端能力封装为REST API，供前端调用，包括模板、任务、上传、校验、生成、预览、溯源、下载。

## 涉及文件

    backend/app/api/
    ├── templates.py
    ├── tasks.py
    ├── documents.py
    ├── trace.py
    └── health.py

    backend/app/main.py

## 输入

REST请求：

    GET /api/templates
    GET /api/templates/{template_id}
    GET /api/templates/{template_id}/requirements
    GET /api/tasks
    POST /api/tasks
    GET /api/tasks/{task_id}
    POST /api/tasks/{task_id}/upload
    POST /api/tasks/{task_id}/validate
    POST /api/tasks/{task_id}/generate
    GET /api/tasks/{task_id}/progress
    GET /api/tasks/{task_id}/outputs
    GET /api/documents/{doc_id}/preview
    GET /api/documents/{doc_id}/trace
    GET /api/trace/{trace_id}
    GET /api/trace/{trace_id}/source-row
    GET /api/documents/{doc_id}/download
    GET /api/tasks/{task_id}/download-zip
    GET /api/tasks/{task_id}/logs

## 输出

统一API响应：

    class ApiSuccess(BaseModel):
        success: Literal[True]
        data: Any
        request_id: str
        timestamp: datetime

    class ApiError(BaseModel):
        success: Literal[False]
        error: ApiErrorDetail
        request_id: str
        timestamp: datetime

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  `/docs` 中能看到所有API。
2.  所有JSON响应包含 `success`、`request_id`、`timestamp`。
3.  找不到任务返回 `TASK_NOT_FOUND`。
4.  找不到文档返回 `DOCUMENT_NOT_FOUND`。
5.  下载接口返回正确Content-Type和文件名。

## 复杂度标记

中复杂度。接口多，但业务逻辑应全部放在service/engine，不要写在路由函数中。

# M17 前端API客户端与类型模块

## 一句话描述

在Vue前端定义TypeScript类型和API请求封装，保证前后端数据结构一致。

## 涉及文件

    frontend/src/types/
    ├── api.ts
    ├── task.ts
    ├── template.ts
    ├── trace.ts
    ├── preview.ts
    └── validation.ts

    frontend/src/api/
    ├── http.ts
    ├── templates.ts
    ├── tasks.ts
    ├── documents.ts
    └── trace.ts

## 输入

后端API响应JSON。

## 输出

TypeScript类型：

    export interface ApiResponse<T> {
      success: boolean
      data?: T
      error?: ApiErrorDetail
      request_id: string
      timestamp: string
    }

    export interface TaskListItem {
      task_id: string
      task_name: string
      template_id: number
      template_name: string
      status: string
      ai_enabled: boolean
      total_rows: number
      success_count: number
      failed_count: number
      created_at: string
      updated_at: string
    }

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  前端能成功调用 `GET /api/templates`。
2.  前端能成功调用 `GET /api/tasks`。
3.  API错误能统一弹出错误信息。
4.  TypeScript编译无类型错误。
5.  所有API路径集中维护，不散落在页面组件中。

## 复杂度标记

低复杂度。

# M18 前端任务管理页面模块

## 一句话描述

实现任务列表、新建任务、文件上传、校验、生成、结果列表的基础页面。

## 涉及文件

    frontend/src/views/
    ├── TaskListView.vue
    ├── TaskCreateView.vue
    └── TaskResultView.vue

    frontend/src/components/
    ├── TemplateSelector.vue
    ├── RequiredTableUploadList.vue
    ├── ValidationReportPanel.vue
    └── OutputDocumentList.vue

## 输入

API数据：

    TemplateListResponse
    TemplateRequirements
    TaskDetail
    ValidationReport
    TaskOutputsResponse

## 输出

用户操作：

    createTask(task_name, template_id, ai_enabled)
    uploadFile(task_id, table_name, file)
    validateTask(task_id)
    generateTask(task_id)
    openDocumentPreview(doc_id)
    downloadDocument(doc_id)
    downloadZip(task_id)

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  用户能在页面选择模板并创建任务。
2.  页面根据模板要求展示需要上传的表。
3.  用户能为每张表上传 `.xlsx`。
4.  点击校验后能展示错误、警告、提示。
5.  生成完成后能看到文档列表，并点击进入预览页。

## 复杂度标记

中复杂度。前端状态流要清晰。

# M19 前端文档溯源预览页面模块

## 一句话描述

实现左侧文档结构化预览、右侧溯源详情和来源Excel行展示。

## 涉及文件

    frontend/src/views/
    └── DocumentTraceView.vue

    frontend/src/components/
    ├── PreviewRenderer.vue
    ├── TraceDetailPanel.vue
    ├── SourceRowTable.vue
    └── DocumentNavBar.vue

## 输入

    PreviewFile
    TraceItem
    SourceRowResponse

## 输出

页面交互状态：

    selectedTraceId: string | null
    selectedTraceItem: TraceItem | null
    sourceRow: SourceRowResponse | null

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  页面能加载并渲染 `preview.json`。
2.  带 `trace_id` 的文本可点击。
3.  点击后右侧展示表名、字段名、文件名、Excel行号、原始值、展示值。
4.  来源行表格中高亮当前字段。
5.  页面提供"下载当前Word"和"返回任务结果"按钮。

## 复杂度标记

中高复杂度。交互不难，但数据结构嵌套较多。

# M20 下载与ZIP打包模块

## 一句话描述

提供单个Word下载和任务内所有Word批量ZIP下载能力。

## 涉及文件

    backend/app/storage/
    └── zip_manager.py

    backend/app/api/
    ├── documents.py
    └── tasks.py

## 输入

    class DownloadDocumentInput(BaseModel):
        doc_id: str

    class DownloadZipInput(BaseModel):
        task_id: str

## 输出

    class FileDownloadResult(BaseModel):
        file_path: Path
        filename: str
        media_type: str

实际HTTP输出：

    application/vnd.openxmlformats-officedocument.wordprocessingml.document
    application/zip

## 可参考旧代码

无。该模块从零开发。

## 验收标准

1.  单个docx可下载并正常打开。
2.  ZIP中只包含该任务成功生成的 `.docx`。
3.  ZIP中不包含 `.trace.json`、`.preview.json`、日志和上传Excel。
4.  文档不存在时返回 `FILE_NOT_FOUND`。
5.  不允许通过构造路径下载任务目录外文件。

## 复杂度标记

低到中复杂度。重点是路径安全。

# M21 测试样例与端到端验收模块

## 一句话描述

建立最小样例配置、Excel、Word模板和自动化测试，验证从上传到下载的完整闭环。

## 涉及文件

    tests/
    ├── fixtures/
    │   ├── config/
    │   │   ├── entity_schema.xlsx
    │   │   └── template_relation.xlsx
    │   ├── templates/
    │   │   └── due_diligence.docx
    │   └── data/
    │       ├── customer_info.xlsx
    │       ├── loan_summary.xlsx
    │       └── collateral_info.xlsx
    ├── test_schema_loader.py
    ├── test_data_loader.py
    ├── test_validator.py
    ├── test_context_builder.py
    ├── test_docx_renderer.py
    ├── test_trace_preview_builder.py
    ├── test_generation_runner.py
    └── test_api_e2e.py

## 输入

测试夹具：

    1个模板
    1张主表 customer_info.xlsx，至少3行
    1张一对一辅表 loan_summary.xlsx
    1张一对多辅表 collateral_info.xlsx

## 输出

    3份docx
    3份trace.json
    3份preview.json
    1个validation_report.json

## 可参考旧代码

可参考旧项目中的：

    word_gen_system/config
    word_gen_system/templates
    word_gen_system_demo_with_marking.ipynb 的测试数据结构

## 验收标准

1.  `pytest` 全部通过。
2.  端到端测试能创建任务、上传3张Excel、校验、生成、查询输出。
3.  生成的docx数量等于主表行数。
4.  每个docx都有对应trace和preview。
5.  trace中的任意一个trace_id可通过API查询到来源行。

## 复杂度标记

中复杂度。测试样例对后续Codex迭代非常重要。

# 三、建议给Codex的逐模块开发提示词模板

## 3.1 通用提示词结构

每次只给Codex一个模块，建议格式如下：

    你是一位资深Python全栈工程师。现在只开发模块 Mxx：{模块名称}。

    背景：
    - 项目是 AI智能文档生成系统 MVP。
    - 当前模块只实现 {模块职责}。
    - 不要实现其它模块。
    - 不要引入审核、RAG、在线编辑、Word批注溯源。

    请完成：
    1. 创建/修改以下文件：
       - ...
    2. 实现以下输入输出模型：
       - ...
    3. 实现以下函数/类：
       - ...
    4. 补充pytest测试：
       - ...
    5. 确保验收标准全部满足。

    旧代码参考：
    - 可参考 xxx
    - 禁止参考 xxx

    输出：
    - 直接修改代码
    - 给出运行测试命令

## 3.2 第一批建议投喂Codex的模块顺序

不要让Codex直接做前端或生成引擎，先做底层：

    第1次：M01 项目骨架与配置模块
    第2次：M02 数据模型与类型定义模块
    第3次：M03 文件路径与任务工作区管理模块
    第4次：M04 SQLite数据库初始化与Repository模块
    第5次：M05 配置Excel加载与同步模块

完成后再继续：

    第6次：M06 模板依赖解析服务
    第7次：M07 任务创建与文件上传
    第8次：M08 Excel业务数据加载
    第9次：M09 生成前校验引擎
    第10次：M10 Context与TraceMap构建

再做核心生成：

    第11次：M11 Word模板渲染
    第12次：M12 AI Prompt提取与AI生成
    第13次：M13 AI段落替换与最终docx生成
    第14次：M14 trace.json与preview.json生成
    第15次：M15 批量生成编排器

最后做接口和前端：

    第16次：M16 FastAPI接口层
    第17次：M17 前端API客户端与类型
    第18次：M18 前端任务管理页面
    第19次：M19 前端文档溯源预览页面
    第20次：M20 下载与ZIP打包
    第21次：M21 测试样例与端到端验收

# 四、模块复杂度总览

  模块                        复杂度   是否需要伪代码   是否第一里程碑
  --------------------------- -------- ---------------- ----------------
  M01 项目骨架与配置          低       否               是
  M02 数据模型与类型定义      低       否               是
  M03 文件路径与任务工作区    中低     否               是
  M04 SQLite与Repository      中       否               是
  M05 配置Excel加载与同步     中       否               是
  M06 模板依赖解析            中低     否               是
  M07 任务创建与文件上传      中       否               是
  M08 Excel业务数据加载       中低     否               是
  M09 生成前校验引擎          高       是               是
  M10 Context与TraceMap构建   高       是               是
  M11 Word模板渲染            中       否               是
  M12 AI Prompt与AI生成       中高     否               是
  M13 AI段落替换              高       是               是
  M14 trace与preview生成      高       是               是
  M15 批量生成编排器          高       是               是
  M16 FastAPI接口层           中       否               是
  M17 前端API客户端与类型     低       否               建议是
  M18 前端任务管理页面        中       否               是
  M19 前端溯源预览页面        中高     否               是
  M20 下载与ZIP打包           中低     否               是
  M21 测试样例与端到端验收    中       否               是

# 五、开发过程中的关键红线

1.  不要恢复 `data.field_name` 主表别名。
2.  模板变量必须统一使用 `{table_name}.{field_name}`。
3.  `role=main` 只表示批量生成驱动表，不改变模板变量路径。
4.  不要实现审核通过、驳回、备注。
5.  不要生成 `.review.json`，除非后续明确恢复审核模块。
6.  不要在Word中写溯源批注。
7.  不要复用旧代码中的智能标记系统。
8.  不要复用旧代码中的RAG模块。
9.  不要复用旧代码中的智能分析引擎。
10. trace和preview必须作为独立JSON产物生成。
11. Web预览基于preview.json，不直接解析docx。
12. 下载的Word必须干净，不包含系统标记。
13. 每完成一个模块都必须有pytest或前端可执行验证。
14. Codex每次只做一个模块，不要跨模块大改。
15. 每个模块完成后先提交，再进入下一个模块。

# 六、第一里程碑验收口径

第一里程碑完成后，应能实现以下完整演示：

    1. 启动后端FastAPI服务
    2. 启动前端Vue服务
    3. 页面选择“客户尽调报告”模板
    4. 创建任务
    5. 上传 customer_info.xlsx、loan_summary.xlsx、collateral_info.xlsx
    6. 点击校验
    7. 校验通过，显示预计生成3份文档
    8. 点击生成
    9. 系统生成3份docx、3份trace.json、3份preview.json
    10. 页面展示生成结果列表
    11. 点击其中一份文档进入溯源预览
    12. 左侧看到文档结构化内容
    13. 点击“客户名称”或“贷款余额”
    14. 右侧展示来源Excel文件、表、字段、行号、原始值、展示值
    15. 点击下载当前Word
    16. 本地Word/WPS可正常打开，且不包含trace标记或系统批注
    17. 点击批量下载ZIP，ZIP中包含3份Word文档

# 七、建议的最小测试数据

## 7.1 主表 customer_info.xlsx

  customer_id   customer_name   industry   region
  ------------- --------------- ---------- --------
  C001          张三公司        制造业     杭州
  C002          李四公司        批发零售   宁波
  C003          王五公司        建筑业     温州

## 7.2 一对一辅表 loan_summary.xlsx

  customer_id   loan_balance   bad_rate   interest_rate
  ------------- -------------- ---------- ---------------
  C001          1200.00        0.018      0.042
  C002          800.00         0.005      0.039
  C003          1500.00        0.032      0.045

## 7.3 一对多辅表 collateral_info.xlsx

  customer_id   collateral_name   eval_amount   mortgage_rate
  ------------- ----------------- ------------- ---------------
  C001          厂房              3000.00       0.50
  C001          设备              500.00        0.30
  C002          商铺              1200.00       0.60

## 7.4 Word模板变量示例

    客户名称：{{ customer_info.customer_name }}
    所属行业：{{ customer_info.industry }}
    贷款余额：{{ loan_summary.loan_balance }}
    不良率：{{ loan_summary.bad_rate }}

    {% if loan_summary.bad_rate > 0.02 %}
    该客户风险水平偏高。
    {% else %}
    该客户风险水平可控。
    {% endif %}

    {%tr for item in collateral_info %}
    {{ item.collateral_name }}
    {{ item.eval_amount }}
    {{ item.mortgage_rate }}
    {%tr endfor %}

    §AIBLOCK0§ 请基于客户基本情况和贷款情况生成风险分析。

# 八、总结

本任务清单的核心目的，是让Codex按照"底层能力 → 生成引擎 → API → 前端 → 端到端测试"的顺序逐步开发，而不是一次性生成完整系统。

最关键的技术模块是：

    M09 生成前校验引擎
    M10 Context与TraceMap构建
    M13 AI段落替换
    M14 trace.json与preview.json生成
    M15 批量生成编排器

最关键的产品闭环是：

    上传Excel
    选择模板
    校验数据
    生成Word
    查看溯源
    下载Word

只要第一里程碑能稳定跑通这个闭环，系统就具备了可演示、可迭代、可继续扩展的基础。
