# AI智能文档生成系统 MVP 数据与接口契约文档

> 版本：MVP V1.0\
> 适用范围：Excel + Word模板批量生成文档、生成溯源索引、Web可视化查看溯源、下载Word/ZIP\
> 技术栈：FastAPI + SQLite + 本地文件系统 + docxtpl + pandas + Vue 3\
> 说明：本文档定义数据库表、JSON文件结构、REST API契约、文件路径契约。开发时应以本文档为准。

# 一、全局约定

## 1.1 ID命名规则

    task_id   = task_{yyyyMMdd}_{HHmmss}_{6位随机字符}
    doc_id    = doc_{uuid}
    trace_id  = trace_{uuid}
    log_id    = SQLite自增ID

示例：

    task_20260613_153000_a1b2c3
    doc_550e8400-e29b-41d4-a716-446655440000
    trace_550e8400-e29b-41d4-a716-446655440001

## 1.2 时间格式

所有时间字段统一使用 ISO 8601 字符串。

    2026-06-13T15:30:00+08:00

数据库中使用 `TEXT` 存储时间。

## 1.3 任务状态枚举

    created       已创建，未上传完整数据
    uploaded      已上传数据，未校验
    validating    校验中
    validated     校验通过
    validation_failed 校验失败
    running       生成中
    completed     生成完成
    partial_failed 部分失败
    failed        生成失败
    deleted       已删除

## 1.4 文档生成状态枚举

    pending       待生成
    running       生成中
    success       生成成功
    failed        生成失败
    ai_partial_failed AI部分失败但文档生成成功

## 1.5 关联关系类型枚举

    main          主表，驱动批量生成
    one_to_one    一对一辅表
    one_to_many   一对多辅表

## 1.6 字段数据类型枚举

    string        字符串
    number        数值
    integer       整数
    date          日期
    datetime      日期时间
    percent       百分比
    boolean       布尔值
    amount        金额

# 二、SQLite数据库表结构

## 2.1 初始化设置

    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = NORMAL;

## 2.2 templates：模板主表

    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY,
        -- 模板ID，对应 template_relation.xlsx 中的 template_id

        template_name TEXT NOT NULL,
        -- 模板名称，例如：客户尽调报告

        template_file TEXT NOT NULL,
        -- 模板文件名，例如：due_diligence.docx

        template_path TEXT NOT NULL,
        -- 模板文件相对路径，例如：templates/due_diligence.docx

        main_table TEXT NOT NULL,
        -- 主表英文名，例如：customer_info

        output_name_pattern TEXT NOT NULL DEFAULT '{template_name}_{primary_key_value}.docx',
        -- 输出文件名模板，MVP默认：模板名_主键值.docx

        ai_enabled_default INTEGER NOT NULL DEFAULT 1,
        -- 是否默认启用AI生成：1启用，0禁用

        is_active INTEGER NOT NULL DEFAULT 1,
        -- 模板是否启用：1启用，0停用

        created_at TEXT NOT NULL,
        -- 创建时间，ISO 8601

        updated_at TEXT NOT NULL
        -- 更新时间，ISO 8601
    );

### 索引

    CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_template_file
    ON templates(template_file);

    CREATE INDEX IF NOT EXISTS idx_templates_main_table
    ON templates(main_table);

    CREATE INDEX IF NOT EXISTS idx_templates_active
    ON templates(is_active);

## 2.3 template_tables：模板依赖表关系

    CREATE TABLE IF NOT EXISTS template_tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- 自增主键

        template_id INTEGER NOT NULL,
        -- 模板ID，关联 templates.id

        table_name TEXT NOT NULL,
        -- 数据表英文名，例如：customer_info

        table_name_cn TEXT NOT NULL DEFAULT '',
        -- 数据表中文名，例如：客户信息表

        role TEXT NOT NULL CHECK (role IN ('main', 'aux')),
        -- 表角色：main主表，aux辅表

        relation_type TEXT NOT NULL CHECK (relation_type IN ('main', 'one_to_one', 'one_to_many')),
        -- 关联类型：main / one_to_one / one_to_many

        main_join_key TEXT NOT NULL DEFAULT '',
        -- 主表关联字段，主表行可为空，辅表必填，例如：customer_id

        table_join_key TEXT NOT NULL DEFAULT '',
        -- 当前表关联字段，主表行可为空，辅表必填，例如：customer_id

        required INTEGER NOT NULL DEFAULT 1,
        -- 是否必需匹配数据：1必需，0非必需

        sort_order INTEGER NOT NULL DEFAULT 0,
        -- 展示顺序

        description TEXT NOT NULL DEFAULT '',
        -- 说明

        created_at TEXT NOT NULL,
        -- 创建时间

        updated_at TEXT NOT NULL,
        -- 更新时间

        FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_template_tables_template_id
    ON template_tables(template_id);

    CREATE INDEX IF NOT EXISTS idx_template_tables_table_name
    ON template_tables(table_name);

    CREATE UNIQUE INDEX IF NOT EXISTS idx_template_tables_unique
    ON template_tables(template_id, table_name);

## 2.4 fields：实体字段字典表

    CREATE TABLE IF NOT EXISTS fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- 自增主键

        table_name TEXT NOT NULL,
        -- 英文表名，例如：customer_info

        table_name_cn TEXT NOT NULL DEFAULT '',
        -- 中文表名，例如：客户信息表

        field_name TEXT NOT NULL,
        -- 英文字段名，例如：customer_name

        field_name_cn TEXT NOT NULL DEFAULT '',
        -- 中文字段名，例如：客户名称

        data_type TEXT NOT NULL DEFAULT 'string'
            CHECK (data_type IN ('string', 'number', 'integer', 'date', 'datetime', 'percent', 'boolean', 'amount')),
        -- 字段数据类型

        is_primary_key INTEGER NOT NULL DEFAULT 0,
        -- 是否主键：1是，0否

        required INTEGER NOT NULL DEFAULT 0,
        -- 是否必填：1必填，0非必填

        display_format TEXT NOT NULL DEFAULT '',
        -- 展示格式，例如：amount_2、percent_2、date_ymd

        description TEXT NOT NULL DEFAULT '',
        -- 字段说明

        created_at TEXT NOT NULL,
        -- 创建时间

        updated_at TEXT NOT NULL
        -- 更新时间
    );

### 索引

    CREATE UNIQUE INDEX IF NOT EXISTS idx_fields_unique
    ON fields(table_name, field_name);

    CREATE INDEX IF NOT EXISTS idx_fields_table_name
    ON fields(table_name);

    CREATE INDEX IF NOT EXISTS idx_fields_primary_key
    ON fields(table_name, is_primary_key);

## 2.5 tasks：生成任务表

    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        -- 任务ID，例如：task_20260613_153000_a1b2c3

        task_name TEXT NOT NULL,
        -- 任务名称

        template_id INTEGER NOT NULL,
        -- 模板ID

        template_name TEXT NOT NULL,
        -- 模板名称，冗余存储便于查询

        status TEXT NOT NULL DEFAULT 'created'
            CHECK (status IN (
                'created',
                'uploaded',
                'validating',
                'validated',
                'validation_failed',
                'running',
                'completed',
                'partial_failed',
                'failed',
                'deleted'
            )),
        -- 任务状态

        ai_enabled INTEGER NOT NULL DEFAULT 1,
        -- 本任务是否启用AI：1启用，0禁用

        main_table TEXT NOT NULL,
        -- 主表英文名

        primary_key_field TEXT NOT NULL,
        -- 主表主键字段名

        total_rows INTEGER NOT NULL DEFAULT 0,
        -- 主表总行数，即预计生成文档数量

        success_count INTEGER NOT NULL DEFAULT 0,
        -- 成功生成文档数量

        failed_count INTEGER NOT NULL DEFAULT 0,
        -- 失败文档数量

        warning_count INTEGER NOT NULL DEFAULT 0,
        -- 警告数量

        error_count INTEGER NOT NULL DEFAULT 0,
        -- 错误数量

        task_dir TEXT NOT NULL,
        -- 任务目录相对路径，例如：tasks/task_xxx

        validation_report_path TEXT NOT NULL DEFAULT '',
        -- 校验报告路径

        error_message TEXT NOT NULL DEFAULT '',
        -- 任务级错误摘要

        created_by TEXT NOT NULL DEFAULT 'system',
        -- 创建人，MVP可默认system

        created_at TEXT NOT NULL,
        -- 创建时间

        updated_at TEXT NOT NULL,
        -- 更新时间

        started_at TEXT,
        -- 生成开始时间

        completed_at TEXT,
        -- 生成完成时间

        FOREIGN KEY (template_id) REFERENCES templates(id)
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_tasks_status
    ON tasks(status);

    CREATE INDEX IF NOT EXISTS idx_tasks_template_id
    ON tasks(template_id);

    CREATE INDEX IF NOT EXISTS idx_tasks_created_at
    ON tasks(created_at);

## 2.6 uploaded_files：任务上传文件表

    CREATE TABLE IF NOT EXISTS uploaded_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- 自增主键

        task_id TEXT NOT NULL,
        -- 任务ID

        table_name TEXT NOT NULL,
        -- 对应业务表名，例如：customer_info

        original_filename TEXT NOT NULL,
        -- 用户上传时的原始文件名

        stored_filename TEXT NOT NULL,
        -- 系统保存后的文件名，通常为 table_name.xlsx

        file_path TEXT NOT NULL,
        -- 文件相对路径，例如：tasks/task_xxx/data/customer_info.xlsx

        file_size INTEGER NOT NULL DEFAULT 0,
        -- 文件大小，单位字节

        file_ext TEXT NOT NULL DEFAULT '.xlsx',
        -- 文件扩展名

        row_count INTEGER NOT NULL DEFAULT 0,
        -- Excel数据行数，不含表头

        column_count INTEGER NOT NULL DEFAULT 0,
        -- Excel字段列数

        checksum TEXT NOT NULL DEFAULT '',
        -- 文件校验值，MVP可为空

        uploaded_at TEXT NOT NULL,
        -- 上传时间

        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_uploaded_files_task_id
    ON uploaded_files(task_id);

    CREATE UNIQUE INDEX IF NOT EXISTS idx_uploaded_files_task_table
    ON uploaded_files(task_id, table_name);

## 2.7 documents：生成文档表

    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        -- 文档ID，例如：doc_uuid

        task_id TEXT NOT NULL,
        -- 所属任务ID

        template_id INTEGER NOT NULL,
        -- 模板ID

        template_name TEXT NOT NULL,
        -- 模板名称

        primary_key_value TEXT NOT NULL,
        -- 当前文档对应的主键值，例如：C001

        output_filename TEXT NOT NULL,
        -- 输出Word文件名，例如：客户尽调报告_C001.docx

        output_path TEXT NOT NULL,
        -- 输出Word相对路径

        trace_filename TEXT NOT NULL,
        -- trace文件名，例如：客户尽调报告_C001.trace.json

        trace_path TEXT NOT NULL,
        -- trace文件相对路径

        preview_filename TEXT NOT NULL,
        -- preview文件名，例如：客户尽调报告_C001.preview.json

        preview_path TEXT NOT NULL,
        -- preview文件相对路径

        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'running', 'success', 'failed', 'ai_partial_failed')),
        -- 文档生成状态

        ai_status TEXT NOT NULL DEFAULT 'not_used'
            CHECK (ai_status IN ('not_used', 'success', 'partial_failed', 'failed')),
        -- AI生成状态

        trace_count INTEGER NOT NULL DEFAULT 0,
        -- 溯源条目数量

        ai_block_count INTEGER NOT NULL DEFAULT 0,
        -- AI段落数量

        error_message TEXT NOT NULL DEFAULT '',
        -- 文档级错误信息

        created_at TEXT NOT NULL,
        -- 创建时间

        updated_at TEXT NOT NULL,
        -- 更新时间

        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
        FOREIGN KEY (template_id) REFERENCES templates(id)
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_documents_task_id
    ON documents(task_id);

    CREATE INDEX IF NOT EXISTS idx_documents_template_id
    ON documents(template_id);

    CREATE INDEX IF NOT EXISTS idx_documents_primary_key_value
    ON documents(primary_key_value);

    CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_task_pk
    ON documents(task_id, primary_key_value);

## 2.8 generation_logs：生成日志表

    CREATE TABLE IF NOT EXISTS generation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- 日志ID

        task_id TEXT NOT NULL,
        -- 任务ID

        doc_id TEXT NOT NULL DEFAULT '',
        -- 文档ID；任务级日志可为空字符串

        level TEXT NOT NULL CHECK (level IN ('debug', 'info', 'warning', 'error')),
        -- 日志级别

        stage TEXT NOT NULL DEFAULT '',
        -- 所属阶段，例如：validate、load_data、render_docx、ai_generate、trace_build

        message TEXT NOT NULL,
        -- 日志摘要

        detail TEXT NOT NULL DEFAULT '',
        -- 日志详情，必要时可存JSON字符串

        created_at TEXT NOT NULL,
        -- 日志时间

        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_generation_logs_task_id
    ON generation_logs(task_id);

    CREATE INDEX IF NOT EXISTS idx_generation_logs_doc_id
    ON generation_logs(doc_id);

    CREATE INDEX IF NOT EXISTS idx_generation_logs_level
    ON generation_logs(level);

    CREATE INDEX IF NOT EXISTS idx_generation_logs_created_at
    ON generation_logs(created_at);

## 2.9 validation_reports：校验报告表

    CREATE TABLE IF NOT EXISTS validation_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        -- 自增主键

        task_id TEXT NOT NULL,
        -- 任务ID

        status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'passed_with_warnings')),
        -- 校验结果

        report_path TEXT NOT NULL,
        -- validation_report.json相对路径

        error_count INTEGER NOT NULL DEFAULT 0,
        -- 错误数量

        warning_count INTEGER NOT NULL DEFAULT 0,
        -- 警告数量

        info_count INTEGER NOT NULL DEFAULT 0,
        -- 信息数量

        created_at TEXT NOT NULL,
        -- 创建时间

        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    );

### 索引

    CREATE INDEX IF NOT EXISTS idx_validation_reports_task_id
    ON validation_reports(task_id);

    CREATE INDEX IF NOT EXISTS idx_validation_reports_status
    ON validation_reports(status);

# 三、核心JSON数据结构

以下使用 TypeScript Interface 作为编码契约。

## 3.1 通用类型

    export type ISODateTimeString = string;

    export type TaskStatus =
      | "created"
      | "uploaded"
      | "validating"
      | "validated"
      | "validation_failed"
      | "running"
      | "completed"
      | "partial_failed"
      | "failed"
      | "deleted";

    export type DocumentStatus =
      | "pending"
      | "running"
      | "success"
      | "failed"
      | "ai_partial_failed";

    export type RelationType =
      | "main"
      | "one_to_one"
      | "one_to_many";

    export type DataType =
      | "string"
      | "number"
      | "integer"
      | "date"
      | "datetime"
      | "percent"
      | "boolean"
      | "amount";

    export type ValidationLevel =
      | "error"
      | "warning"
      | "info";

## 3.2 TraceItem：溯源条目模型

    export interface TraceItem {
      trace_id: string;
      // 溯源条目唯一ID，例如 trace_uuid

      var_path: string;
      // 模板变量路径，例如 customer_info.customer_name

      table_name: string;
      // 来源表英文名，例如 customer_info

      table_name_cn: string;
      // 来源表中文名，例如 客户信息表

      field_name: string;
      // 来源字段英文名，例如 customer_name

      field_name_cn: string;
      // 来源字段中文名，例如 客户名称

      source_file: string;
      // 来源Excel文件名，例如 customer_info.xlsx

      source_file_path: string;
      // 来源Excel相对路径，例如 tasks/task_xxx/data/customer_info.xlsx

      pk_field: string;
      // 当前文档主键字段名，例如 customer_id

      pk_value: string;
      // 当前文档主键值，例如 C001

      row_index: number;
      // pandas中的0-based数据行号，不含表头

      excel_row_number: number;
      // Excel真实行号，通常 row_index + 2

      column_index: number | null;
      // Excel列索引，0-based；无法确定时为null

      excel_column_letter: string | null;
      // Excel列字母，例如 A、B、AA；无法确定时为null

      raw_value: string | number | boolean | null;
      // Excel原始值

      display_value: string;
      // 渲染到Word或预览中的展示值

      value_type: DataType;
      // 字段类型

      display_format: string;
      // 展示格式，例如 amount_2、percent_2

      occurrence_index: number;
      // 同一变量在文档中的第几次出现，从0开始

      source_relation_type: RelationType;
      // 来源表关系类型

      created_at: ISODateTimeString;
      // 溯源条目创建时间
    }

## 3.3 .trace.json：溯源索引文件结构

    export interface TraceFile {
      schema_version: "1.0";

      doc_id: string;
      task_id: string;

      template_id: number;
      template_name: string;
      template_file: string;

      output_file: string;
      output_path: string;

      main_table: string;
      main_table_cn: string;

      primary_key_field: string;
      primary_key_value: string;

      generated_at: ISODateTimeString;

      source_files: SourceFileInfo[];

      trace_items: TraceItem[];

      ai_blocks: AIBlockTrace[];

      statistics: TraceStatistics;
    }

    export interface SourceFileInfo {
      table_name: string;
      table_name_cn: string;
      filename: string;
      path: string;
      row_count: number;
      column_count: number;
    }

    export interface AIBlockTrace {
      block_id: string;
      // 例如 AIBLOCK0

      marker: string;
      // 例如 §AIBLOCK0§

      status: "not_used" | "success" | "failed";

      prompt_template: string;
      // 原始批注prompt模板

      prompt_rendered: string;
      // 变量渲染后的prompt

      model: string;
      // 例如 deepseek-chat

      input_variables: string[];
      // prompt中用到的变量路径列表

      generated_text: string;
      // AI生成文本，失败时为空字符串

      error_message: string;
      // 失败原因，成功时为空字符串

      started_at: ISODateTimeString | null;

      completed_at: ISODateTimeString | null;
    }

    export interface TraceStatistics {
      trace_item_count: number;
      ai_block_count: number;
      source_file_count: number;
      table_count: number;
    }

### .trace.json 示例

    {
      "schema_version": "1.0",
      "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
      "task_id": "task_20260613_153000_a1b2c3",
      "template_id": 1,
      "template_name": "客户尽调报告",
      "template_file": "due_diligence.docx",
      "output_file": "客户尽调报告_C001.docx",
      "output_path": "tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.docx",
      "main_table": "customer_info",
      "main_table_cn": "客户信息表",
      "primary_key_field": "customer_id",
      "primary_key_value": "C001",
      "generated_at": "2026-06-13T15:30:00+08:00",
      "source_files": [
        {
          "table_name": "customer_info",
          "table_name_cn": "客户信息表",
          "filename": "customer_info.xlsx",
          "path": "tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
          "row_count": 3,
          "column_count": 8
        }
      ],
      "trace_items": [
        {
          "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001",
          "var_path": "customer_info.customer_name",
          "table_name": "customer_info",
          "table_name_cn": "客户信息表",
          "field_name": "customer_name",
          "field_name_cn": "客户名称",
          "source_file": "customer_info.xlsx",
          "source_file_path": "tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
          "pk_field": "customer_id",
          "pk_value": "C001",
          "row_index": 0,
          "excel_row_number": 2,
          "column_index": 1,
          "excel_column_letter": "B",
          "raw_value": "张三公司",
          "display_value": "张三公司",
          "value_type": "string",
          "display_format": "",
          "occurrence_index": 0,
          "source_relation_type": "main",
          "created_at": "2026-06-13T15:30:00+08:00"
        }
      ],
      "ai_blocks": [
        {
          "block_id": "AIBLOCK0",
          "marker": "§AIBLOCK0§",
          "status": "success",
          "prompt_template": "请基于客户{{ customer_info.customer_name }}生成风险分析。",
          "prompt_rendered": "请基于客户张三公司生成风险分析。",
          "model": "deepseek-chat",
          "input_variables": ["customer_info.customer_name"],
          "generated_text": "该客户经营情况整体稳定，但仍需关注现金流变化。",
          "error_message": "",
          "started_at": "2026-06-13T15:30:01+08:00",
          "completed_at": "2026-06-13T15:30:05+08:00"
        }
      ],
      "statistics": {
        "trace_item_count": 1,
        "ai_block_count": 1,
        "source_file_count": 1,
        "table_count": 1
      }
    }

## 3.4 .review.json：审核记录结构

> MVP当前不做审核、驳回、备注流程。\
> 该结构仅作为扩展预留。MVP默认不生成 `.review.json`，也不提供写入审核记录的API。\
> 如果后续需要恢复审核功能，可基于此结构扩展。

    export interface ReviewFile {
      schema_version: "1.0";

      doc_id: string;
      task_id: string;

      review_mode: "disabled" | "view_only" | "manual_review";

      status:
        | "not_applicable"
        | "not_started"
        | "viewed"
        | "downloaded"
        | "completed";

      reviewer: string;
      // MVP可为空字符串

      reviewed_at: ISODateTimeString | null;

      trace_reviews: TraceReviewItem[];

      download_records: DownloadRecord[];
    }

    export interface TraceReviewItem {
      trace_id: string;

      status:
        | "not_checked"
        | "checked";

      checked_at: ISODateTimeString | null;

      checked_by: string;
    }

    export interface DownloadRecord {
      downloaded_by: string;

      downloaded_at: ISODateTimeString;

      download_type: "single_docx" | "zip";
    }

### .review.json 示例

    {
      "schema_version": "1.0",
      "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
      "task_id": "task_20260613_153000_a1b2c3",
      "review_mode": "disabled",
      "status": "not_applicable",
      "reviewer": "",
      "reviewed_at": null,
      "trace_reviews": [],
      "download_records": []
    }

## 3.5 meta.json：任务元数据结构

    export interface TaskMeta {
      schema_version: "1.0";

      task_id: string;
      task_name: string;

      template_id: number;
      template_name: string;
      template_file: string;

      ai_enabled: boolean;

      status: TaskStatus;

      main_table: string;
      main_table_cn: string;

      primary_key_field: string;

      required_tables: RequiredTable[];

      uploaded_files: UploadedFileMeta[];

      output_summary: OutputSummary;

      paths: TaskPaths;

      created_at: ISODateTimeString;
      updated_at: ISODateTimeString;
      started_at: ISODateTimeString | null;
      completed_at: ISODateTimeString | null;
    }

    export interface RequiredTable {
      table_name: string;
      table_name_cn: string;
      role: "main" | "aux";
      relation_type: RelationType;
      main_join_key: string;
      table_join_key: string;
      required: boolean;
    }

    export interface UploadedFileMeta {
      table_name: string;
      original_filename: string;
      stored_filename: string;
      path: string;
      row_count: number;
      column_count: number;
      uploaded_at: ISODateTimeString;
    }

    export interface OutputSummary {
      total_rows: number;
      success_count: number;
      failed_count: number;
      warning_count: number;
      error_count: number;
      document_ids: string[];
    }

    export interface TaskPaths {
      task_dir: string;
      data_dir: string;
      output_dir: string;
      validation_dir: string;
      logs_dir: string;
    }

### meta.json 示例

    {
      "schema_version": "1.0",
      "task_id": "task_20260613_153000_a1b2c3",
      "task_name": "客户尽调报告批量生成",
      "template_id": 1,
      "template_name": "客户尽调报告",
      "template_file": "due_diligence.docx",
      "ai_enabled": true,
      "status": "completed",
      "main_table": "customer_info",
      "main_table_cn": "客户信息表",
      "primary_key_field": "customer_id",
      "required_tables": [
        {
          "table_name": "customer_info",
          "table_name_cn": "客户信息表",
          "role": "main",
          "relation_type": "main",
          "main_join_key": "",
          "table_join_key": "",
          "required": true
        },
        {
          "table_name": "loan_summary",
          "table_name_cn": "贷款汇总表",
          "role": "aux",
          "relation_type": "one_to_one",
          "main_join_key": "customer_id",
          "table_join_key": "customer_id",
          "required": true
        }
      ],
      "uploaded_files": [
        {
          "table_name": "customer_info",
          "original_filename": "客户信息表.xlsx",
          "stored_filename": "customer_info.xlsx",
          "path": "tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
          "row_count": 3,
          "column_count": 8,
          "uploaded_at": "2026-06-13T15:20:00+08:00"
        }
      ],
      "output_summary": {
        "total_rows": 3,
        "success_count": 3,
        "failed_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "document_ids": [
          "doc_550e8400-e29b-41d4-a716-446655440000"
        ]
      },
      "paths": {
        "task_dir": "tasks/task_20260613_153000_a1b2c3",
        "data_dir": "tasks/task_20260613_153000_a1b2c3/data",
        "output_dir": "tasks/task_20260613_153000_a1b2c3/output",
        "validation_dir": "tasks/task_20260613_153000_a1b2c3/validation",
        "logs_dir": "tasks/task_20260613_153000_a1b2c3/logs"
      },
      "created_at": "2026-06-13T15:15:00+08:00",
      "updated_at": "2026-06-13T15:30:10+08:00",
      "started_at": "2026-06-13T15:25:00+08:00",
      "completed_at": "2026-06-13T15:30:10+08:00"
    }

## 3.6 文档预览 preview.json 结构

    export interface PreviewFile {
      schema_version: "1.0";

      doc_id: string;
      task_id: string;

      title: string;

      output_file: string;

      primary_key_value: string;

      blocks: PreviewBlock[];

      created_at: ISODateTimeString;
    }

    export type PreviewBlock =
      | PreviewHeadingBlock
      | PreviewParagraphBlock
      | PreviewTableBlock;

    export interface PreviewHeadingBlock {
      type: "heading";
      block_id: string;
      level: 1 | 2 | 3 | 4 | 5 | 6;
      text: string;
    }

    export interface PreviewParagraphBlock {
      type: "paragraph";
      block_id: string;
      runs: PreviewRun[];
    }

    export interface PreviewTableBlock {
      type: "table";
      block_id: string;
      headers: PreviewTableCell[];
      rows: PreviewTableCell[][];
    }

    export interface PreviewRun {
      text: string;
      trace_id?: string;
      ai_block_id?: string;
      style?: PreviewRunStyle;
    }

    export interface PreviewTableCell {
      text: string;
      trace_id?: string;
      ai_block_id?: string;
    }

    export interface PreviewRunStyle {
      bold?: boolean;
      italic?: boolean;
      underline?: boolean;
    }

### preview.json 示例

    {
      "schema_version": "1.0",
      "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
      "task_id": "task_20260613_153000_a1b2c3",
      "title": "客户尽调报告_C001.docx",
      "output_file": "客户尽调报告_C001.docx",
      "primary_key_value": "C001",
      "blocks": [
        {
          "type": "heading",
          "block_id": "block_001",
          "level": 1,
          "text": "客户尽调报告"
        },
        {
          "type": "paragraph",
          "block_id": "block_002",
          "runs": [
            {
              "text": "客户名称："
            },
            {
              "text": "张三公司",
              "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001"
            }
          ]
        },
        {
          "type": "table",
          "block_id": "block_003",
          "headers": [
            {
              "text": "担保品名称"
            },
            {
              "text": "评估价值"
            }
          ],
          "rows": [
            [
              {
                "text": "厂房",
                "trace_id": "trace_550e8400-e29b-41d4-a716-446655440101"
              },
              {
                "text": "3000.00",
                "trace_id": "trace_550e8400-e29b-41d4-a716-446655440102"
              }
            ]
          ]
        }
      ],
      "created_at": "2026-06-13T15:30:00+08:00"
    }

## 3.7 validation_report.json 结构

    export interface ValidationReport {
      schema_version: "1.0";

      task_id: string;

      status: "passed" | "failed" | "passed_with_warnings";

      summary: {
        error_count: number;
        warning_count: number;
        info_count: number;
      };

      items: ValidationItem[];

      created_at: ISODateTimeString;
    }

    export interface ValidationItem {
      level: ValidationLevel;

      code: string;
      // 例如 missing_table、missing_field、duplicated_pk

      message: string;

      table_name?: string;

      field_name?: string;

      template_id?: number;

      template_file?: string;

      suggestion?: string;

      detail?: Record<string, unknown>;
    }

### validation_report.json 示例

    {
      "schema_version": "1.0",
      "task_id": "task_20260613_153000_a1b2c3",
      "status": "failed",
      "summary": {
        "error_count": 1,
        "warning_count": 1,
        "info_count": 0
      },
      "items": [
        {
          "level": "error",
          "code": "missing_field",
          "message": "模板引用字段 loan_summary.loan_balance，但上传数据中缺少该字段。",
          "table_name": "loan_summary",
          "field_name": "loan_balance",
          "template_id": 1,
          "template_file": "due_diligence.docx",
          "suggestion": "请在 loan_summary.xlsx 中增加 loan_balance 字段。"
        },
        {
          "level": "warning",
          "code": "empty_optional_aux_table",
          "message": "非必需辅表 collateral_info 未匹配到客户 C001 的数据，将渲染为空列表。",
          "table_name": "collateral_info",
          "suggestion": "如该客户确无担保品，可忽略此提示。"
        }
      ],
      "created_at": "2026-06-13T15:25:00+08:00"
    }

# 四、REST API契约

## 4.1 通用响应格式

### 成功响应

    export interface ApiSuccess<T> {
      success: true;
      data: T;
      request_id: string;
      timestamp: ISODateTimeString;
    }

### 错误响应

    export interface ApiError {
      success: false;
      error: {
        code: string;
        message: string;
        detail?: unknown;
      };
      request_id: string;
      timestamp: ISODateTimeString;
    }

### 错误响应示例

    {
      "success": false,
      "error": {
        "code": "TASK_NOT_FOUND",
        "message": "任务不存在：task_20260613_153000_a1b2c3",
        "detail": {
          "task_id": "task_20260613_153000_a1b2c3"
        }
      },
      "request_id": "req_550e8400-e29b-41d4-a716-446655440999",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## 4.2 错误码约定

    BAD_REQUEST             请求参数错误
    TASK_NOT_FOUND          任务不存在
    TEMPLATE_NOT_FOUND      模板不存在
    DOCUMENT_NOT_FOUND      文档不存在
    TRACE_NOT_FOUND         溯源条目不存在
    FILE_NOT_FOUND          文件不存在
    VALIDATION_FAILED       校验失败
    TASK_STATUS_INVALID     当前任务状态不允许执行该操作
    UPLOAD_FILE_INVALID     上传文件不合法
    GENERATION_FAILED       生成失败
    INTERNAL_ERROR          系统内部错误

# 4.3 模板相关API

## API 1：获取模板列表

### `GET /api/templates`

### Query Parameters

    active_only?: boolean 默认 true

### Response Body

    {
      "success": true,
      "data": {
        "items": [
          {
            "template_id": 1,
            "template_name": "客户尽调报告",
            "template_file": "due_diligence.docx",
            "main_table": "customer_info",
            "ai_enabled_default": true,
            "is_active": true,
            "created_at": "2026-06-13T15:00:00+08:00",
            "updated_at": "2026-06-13T15:00:00+08:00"
          }
        ],
        "total": 1
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 2：获取模板详情

### `GET /api/templates/{template_id}`

### Response Body

    {
      "success": true,
      "data": {
        "template_id": 1,
        "template_name": "客户尽调报告",
        "template_file": "due_diligence.docx",
        "template_path": "templates/due_diligence.docx",
        "main_table": "customer_info",
        "output_name_pattern": "{template_name}_{primary_key_value}.docx",
        "ai_enabled_default": true,
        "tables": [
          {
            "table_name": "customer_info",
            "table_name_cn": "客户信息表",
            "role": "main",
            "relation_type": "main",
            "main_join_key": "",
            "table_join_key": "",
            "required": true
          },
          {
            "table_name": "loan_summary",
            "table_name_cn": "贷款汇总表",
            "role": "aux",
            "relation_type": "one_to_one",
            "main_join_key": "customer_id",
            "table_join_key": "customer_id",
            "required": true
          }
        ]
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 3：获取模板依赖要求

### `GET /api/templates/{template_id}/requirements`

### Response Body

    {
      "success": true,
      "data": {
        "template_id": 1,
        "template_name": "客户尽调报告",
        "main_table": "customer_info",
        "primary_key_field": "customer_id",
        "required_tables": [
          {
            "table_name": "customer_info",
            "table_name_cn": "客户信息表",
            "role": "main",
            "relation_type": "main",
            "required": true,
            "fields": [
              {
                "field_name": "customer_id",
                "field_name_cn": "客户编号",
                "data_type": "string",
                "is_primary_key": true,
                "required": true
              },
              {
                "field_name": "customer_name",
                "field_name_cn": "客户名称",
                "data_type": "string",
                "is_primary_key": false,
                "required": true
              }
            ]
          }
        ]
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

# 4.4 任务相关API

## API 4：获取任务列表

### `GET /api/tasks`

### Query Parameters

    status?: string
    page?: number 默认 1
    page_size?: number 默认 20

### Response Body

    {
      "success": true,
      "data": {
        "items": [
          {
            "task_id": "task_20260613_153000_a1b2c3",
            "task_name": "客户尽调报告批量生成",
            "template_id": 1,
            "template_name": "客户尽调报告",
            "status": "completed",
            "ai_enabled": true,
            "total_rows": 3,
            "success_count": 3,
            "failed_count": 0,
            "created_at": "2026-06-13T15:15:00+08:00",
            "updated_at": "2026-06-13T15:30:10+08:00"
          }
        ],
        "page": 1,
        "page_size": 20,
        "total": 1
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 5：创建任务

### `POST /api/tasks`

### Request Body

    {
      "task_name": "客户尽调报告批量生成",
      "template_id": 1,
      "ai_enabled": true
    }

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "task_name": "客户尽调报告批量生成",
        "template_id": 1,
        "template_name": "客户尽调报告",
        "status": "created",
        "task_dir": "tasks/task_20260613_153000_a1b2c3",
        "required_tables": [
          {
            "table_name": "customer_info",
            "table_name_cn": "客户信息表",
            "role": "main",
            "relation_type": "main",
            "required": true
          },
          {
            "table_name": "loan_summary",
            "table_name_cn": "贷款汇总表",
            "role": "aux",
            "relation_type": "one_to_one",
            "required": true
          }
        ],
        "created_at": "2026-06-13T15:15:00+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:15:00+08:00"
    }

## API 6：获取任务详情

### `GET /api/tasks/{task_id}`

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "task_name": "客户尽调报告批量生成",
        "template_id": 1,
        "template_name": "客户尽调报告",
        "status": "completed",
        "ai_enabled": true,
        "main_table": "customer_info",
        "primary_key_field": "customer_id",
        "total_rows": 3,
        "success_count": 3,
        "failed_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "task_dir": "tasks/task_20260613_153000_a1b2c3",
        "validation_report_path": "tasks/task_20260613_153000_a1b2c3/validation/validation_report.json",
        "created_at": "2026-06-13T15:15:00+08:00",
        "updated_at": "2026-06-13T15:30:10+08:00",
        "started_at": "2026-06-13T15:25:00+08:00",
        "completed_at": "2026-06-13T15:30:10+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 7：上传任务数据文件

### `POST /api/tasks/{task_id}/upload`

### Content-Type

    multipart/form-data

### Form Fields

    table_name: string
    file: .xlsx

### Request 示例

    POST /api/tasks/task_20260613_153000_a1b2c3/upload
    Content-Type: multipart/form-data

    table_name=customer_info
    file=customer_info.xlsx

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "table_name": "customer_info",
        "original_filename": "客户信息表.xlsx",
        "stored_filename": "customer_info.xlsx",
        "file_path": "tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
        "file_size": 20480,
        "row_count": 3,
        "column_count": 8,
        "uploaded_at": "2026-06-13T15:20:00+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:20:00+08:00"
    }

## API 8：执行任务校验

### `POST /api/tasks/{task_id}/validate`

### Request Body

    {
      "force": false
    }

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "status": "passed",
        "report_path": "tasks/task_20260613_153000_a1b2c3/validation/validation_report.json",
        "summary": {
          "error_count": 0,
          "warning_count": 0,
          "info_count": 2
        },
        "items": [
          {
            "level": "info",
            "code": "main_table_detected",
            "message": "主表 customer_info 共3行，将生成3份文档。"
          }
        ]
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:25:00+08:00"
    }

## API 9：开始生成任务

### `POST /api/tasks/{task_id}/generate`

### Request Body

    {
      "force": false,
      "ai_enabled": true
    }

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "status": "running",
        "message": "生成任务已开始。",
        "started_at": "2026-06-13T15:26:00+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:26:00+08:00"
    }

### 状态限制

    允许执行状态：
    validated
    completed 且 force=true
    partial_failed 且 force=true
    failed 且 force=true

    不允许执行状态：
    created
    uploaded
    validating
    running
    deleted

## API 10：获取任务生成进度

### `GET /api/tasks/{task_id}/progress`

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "status": "running",
        "total_rows": 3,
        "success_count": 1,
        "failed_count": 0,
        "current_primary_key_value": "C002",
        "progress_percent": 33.33,
        "message": "正在生成第2份文档：C002"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:27:00+08:00"
    }

## API 11：获取任务输出文档列表

### `GET /api/tasks/{task_id}/outputs`

### Response Body

    {
      "success": true,
      "data": {
        "task_id": "task_20260613_153000_a1b2c3",
        "items": [
          {
            "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
            "primary_key_value": "C001",
            "output_filename": "客户尽调报告_C001.docx",
            "status": "success",
            "ai_status": "success",
            "trace_count": 12,
            "ai_block_count": 1,
            "created_at": "2026-06-13T15:30:00+08:00"
          }
        ],
        "total": 1
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

# 4.5 文档与溯源API

## API 12：获取文档预览

### `GET /api/documents/{doc_id}/preview`

### Response Body

    {
      "success": true,
      "data": {
        "schema_version": "1.0",
        "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
        "task_id": "task_20260613_153000_a1b2c3",
        "title": "客户尽调报告_C001.docx",
        "output_file": "客户尽调报告_C001.docx",
        "primary_key_value": "C001",
        "blocks": [
          {
            "type": "heading",
            "block_id": "block_001",
            "level": 1,
            "text": "客户尽调报告"
          },
          {
            "type": "paragraph",
            "block_id": "block_002",
            "runs": [
              {
                "text": "客户名称："
              },
              {
                "text": "张三公司",
                "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001"
              }
            ]
          }
        ],
        "created_at": "2026-06-13T15:30:00+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 13：获取文档完整溯源索引

### `GET /api/documents/{doc_id}/trace`

### Response Body

    {
      "success": true,
      "data": {
        "schema_version": "1.0",
        "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000",
        "task_id": "task_20260613_153000_a1b2c3",
        "template_id": 1,
        "template_name": "客户尽调报告",
        "output_file": "客户尽调报告_C001.docx",
        "main_table": "customer_info",
        "primary_key_field": "customer_id",
        "primary_key_value": "C001",
        "trace_items": [],
        "ai_blocks": [],
        "statistics": {
          "trace_item_count": 12,
          "ai_block_count": 1,
          "source_file_count": 3,
          "table_count": 3
        }
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

说明：实际返回可包含完整 `trace_items`。如果数据过大，后续可增加分页参数。

## API 14：获取单个溯源条目详情

### `GET /api/trace/{trace_id}`

### Response Body

    {
      "success": true,
      "data": {
        "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001",
        "var_path": "customer_info.customer_name",
        "table_name": "customer_info",
        "table_name_cn": "客户信息表",
        "field_name": "customer_name",
        "field_name_cn": "客户名称",
        "source_file": "customer_info.xlsx",
        "source_file_path": "tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
        "pk_field": "customer_id",
        "pk_value": "C001",
        "row_index": 0,
        "excel_row_number": 2,
        "column_index": 1,
        "excel_column_letter": "B",
        "raw_value": "张三公司",
        "display_value": "张三公司",
        "value_type": "string",
        "display_format": "",
        "occurrence_index": 0,
        "source_relation_type": "main",
        "created_at": "2026-06-13T15:30:00+08:00"
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 15：获取溯源来源行数据

### `GET /api/trace/{trace_id}/source-row`

### Response Body

    {
      "success": true,
      "data": {
        "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001",
        "table_name": "customer_info",
        "table_name_cn": "客户信息表",
        "source_file": "customer_info.xlsx",
        "excel_row_number": 2,
        "highlight_field": "customer_name",
        "columns": [
          {
            "field_name": "customer_id",
            "field_name_cn": "客户编号",
            "excel_column_letter": "A",
            "data_type": "string"
          },
          {
            "field_name": "customer_name",
            "field_name_cn": "客户名称",
            "excel_column_letter": "B",
            "data_type": "string"
          }
        ],
        "row": {
          "customer_id": "C001",
          "customer_name": "张三公司"
        }
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 16：下载单个Word文档

### `GET /api/documents/{doc_id}/download`

### Response

    Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
    Content-Disposition: attachment; filename="客户尽调报告_C001.docx"

错误响应仍使用JSON：

    {
      "success": false,
      "error": {
        "code": "FILE_NOT_FOUND",
        "message": "Word文件不存在。",
        "detail": {
          "doc_id": "doc_550e8400-e29b-41d4-a716-446655440000"
        }
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

## API 17：批量下载任务ZIP

### `GET /api/tasks/{task_id}/download-zip`

### Response

    Content-Type: application/zip
    Content-Disposition: attachment; filename="task_20260613_153000_a1b2c3_outputs.zip"

ZIP内容：

    客户尽调报告_C001.docx
    客户尽调报告_C002.docx
    客户尽调报告_C003.docx

默认只打包 `.docx`，不打包 `.trace.json`、`.preview.json`。

## API 18：获取任务日志

### `GET /api/tasks/{task_id}/logs`

### Query Parameters

    level?: debug | info | warning | error
    page?: number 默认 1
    page_size?: number 默认 100

### Response Body

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": 1,
            "task_id": "task_20260613_153000_a1b2c3",
            "doc_id": "",
            "level": "info",
            "stage": "validate",
            "message": "任务校验通过。",
            "detail": "",
            "created_at": "2026-06-13T15:25:00+08:00"
          }
        ],
        "page": 1,
        "page_size": 100,
        "total": 1
      },
      "request_id": "req_xxx",
      "timestamp": "2026-06-13T15:30:00+08:00"
    }

# 五、文件系统路径契约

## 5.1 项目根目录

    project_root/

所有路径均为相对 `project_root` 的相对路径。

## 5.2 配置目录

    config/
    ├── entity_schema.xlsx
    ├── template_relation.xlsx
    └── db.sqlite

### 说明

  路径                              说明                       访问方
  --------------------------------- -------------------------- ------------------------
  `config/entity_schema.xlsx`       实体字段Schema事实来源     启动同步脚本、后端服务
  `config/template_relation.xlsx`   模板与数据表关系事实来源   启动同步脚本、后端服务
  `config/db.sqlite`                SQLite数据库               Web服务、生成引擎

## 5.3 模板目录

    templates/
    ├── due_diligence.docx
    ├── branch_report.docx
    └── contract_material.docx

### 命名规则

    {template_file}.docx

示例：

    due_diligence.docx
    branch_report.docx

### 访问方

  访问方       权限
  ------------ ----------------------------
  生成引擎     读取模板
  Web服务      读取模板元数据，不直接修改
  模板管理员   手工维护MVP模板文件

## 5.4 任务目录

    tasks/
    └── {task_id}/
        ├── meta.json
        ├── data/
        ├── validation/
        ├── output/
        └── logs/

示例：

    tasks/task_20260613_153000_a1b2c3/

## 5.5 任务元数据文件

    tasks/{task_id}/meta.json

### 访问方

  访问方     权限
  ---------- -----------------------------
  Web服务    读写
  生成引擎   读写
  前端       通过API读取，不直接访问文件

## 5.6 上传数据目录

    tasks/{task_id}/data/

### 文件命名规则

    {table_name}.xlsx

示例：

    tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx
    tasks/task_20260613_153000_a1b2c3/data/loan_summary.xlsx
    tasks/task_20260613_153000_a1b2c3/data/collateral_info.xlsx

### 规则

1.  每张业务表一个Excel文件。
2.  文件名必须与 `table_name` 对应。
3.  用户原始文件名记录在数据库 `uploaded_files.original_filename`。
4.  系统保存文件名使用 `{table_name}.xlsx`。
5.  生成引擎只读取该目录下当前任务的数据。

## 5.7 校验目录

    tasks/{task_id}/validation/
    └── validation_report.json

### 文件路径

    tasks/{task_id}/validation/validation_report.json

### 访问方

  访问方     权限
  ---------- -------------
  校验模块   写入
  Web服务    读取
  前端       通过API读取

## 5.8 输出目录

    tasks/{task_id}/output/

每份文档包含三类文件：

    {safe_template_name}_{safe_primary_key_value}.docx
    {safe_template_name}_{safe_primary_key_value}.trace.json
    {safe_template_name}_{safe_primary_key_value}.preview.json

示例：

    tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.docx
    tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.trace.json
    tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.preview.json

## 5.9 输出文件名安全规则

原始规则：

    {template_name}_{primary_key_value}.docx

需要进行文件名安全转换。

### 非法字符替换

以下字符统一替换为下划线 `_`：

    \ / : * ? " < > | 空格

### 长度限制

    最终文件名不超过 120 个字符

如果超过，截断并追加6位hash。

示例：

    客户尽调报告_某某特别长客户名称_x7a9c2.docx

## 5.10 日志目录

    tasks/{task_id}/logs/
    └── generation.log

### 文件路径

    tasks/{task_id}/logs/generation.log

### 说明

1.  数据库 `generation_logs` 存结构化日志。
2.  `generation.log` 存文本日志。
3.  两者内容可以不完全一致，但关键错误必须写入数据库。

## 5.11 临时目录

    temp/
    └── {task_id}/

用途：

1.  docxtpl中间文件。
2.  AI处理临时文件。
3.  ZIP打包临时文件。

规则：

1.  任务完成后可清理。
2.  Web服务不得直接暴露该目录。
3.  不允许用户下载临时目录文件。

## 5.12 ZIP下载路径

生成ZIP时临时写入：

    temp/{task_id}/{task_id}_outputs.zip

下载文件名：

    {task_id}_outputs.zip

ZIP内只包含：

    *.docx

默认不包含：

    *.trace.json
    *.preview.json
    validation_report.json
    generation.log

# 六、生成脚本与Web服务路径访问边界

## 6.1 生成引擎访问路径

生成引擎可访问：

    config/entity_schema.xlsx
    config/template_relation.xlsx
    config/db.sqlite
    templates/{template_file}.docx
    tasks/{task_id}/meta.json
    tasks/{task_id}/data/*.xlsx
    tasks/{task_id}/validation/validation_report.json
    tasks/{task_id}/output/*.docx
    tasks/{task_id}/output/*.trace.json
    tasks/{task_id}/output/*.preview.json
    tasks/{task_id}/logs/generation.log
    temp/{task_id}/

生成引擎不得访问：

    其他 task_id 的 data 目录
    其他 task_id 的 output 目录
    项目根目录之外的任意路径

## 6.2 Web服务访问路径

Web服务可访问：

    config/db.sqlite
    tasks/{task_id}/meta.json
    tasks/{task_id}/data/{table_name}.xlsx
    tasks/{task_id}/validation/validation_report.json
    tasks/{task_id}/output/{filename}.docx
    tasks/{task_id}/output/{filename}.trace.json
    tasks/{task_id}/output/{filename}.preview.json
    tasks/{task_id}/logs/generation.log
    temp/{task_id}/{task_id}_outputs.zip

Web服务不得直接向前端暴露真实绝对路径。

API返回路径必须是相对路径，例如：

    tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.docx

不得返回：

    F:\资料\AI\AI-Document-GS\...
    /home/user/project/...

## 6.3 前端访问规则

前端不直接访问文件系统。

前端只能通过API访问：

    GET /api/tasks
    GET /api/tasks/{task_id}
    GET /api/tasks/{task_id}/outputs
    GET /api/documents/{doc_id}/preview
    GET /api/trace/{trace_id}
    GET /api/trace/{trace_id}/source-row
    GET /api/documents/{doc_id}/download
    GET /api/tasks/{task_id}/download-zip

# 七、最小开发实现建议

## 7.1 后端模块划分

    app/
    ├── main.py
    ├── api/
    │   ├── templates.py
    │   ├── tasks.py
    │   ├── documents.py
    │   └── trace.py
    ├── core/
    │   ├── config.py
    │   ├── errors.py
    │   └── response.py
    ├── db/
    │   ├── connection.py
    │   ├── schema.sql
    │   └── repositories.py
    ├── engine/
    │   ├── schema_loader.py
    │   ├── data_loader.py
    │   ├── validator.py
    │   ├── context_builder.py
    │   ├── docx_renderer.py
    │   ├── ai_generator.py
    │   ├── trace_builder.py
    │   └── generation_runner.py
    ├── models/
    │   ├── task_models.py
    │   ├── trace_models.py
    │   ├── preview_models.py
    │   └── validation_models.py
    └── storage/
        ├── paths.py
        ├── file_manager.py
        └── zip_manager.py

## 7.2 前端模块划分

    frontend/
    ├── src/
    │   ├── api/
    │   │   ├── templates.ts
    │   │   ├── tasks.ts
    │   │   ├── documents.ts
    │   │   └── trace.ts
    │   ├── views/
    │   │   ├── TaskListView.vue
    │   │   ├── TaskCreateView.vue
    │   │   ├── TaskResultView.vue
    │   │   └── DocumentTraceView.vue
    │   ├── components/
    │   │   ├── PreviewRenderer.vue
    │   │   ├── TraceDetailPanel.vue
    │   │   └── SourceRowTable.vue
    │   └── types/
    │       ├── api.ts
    │       ├── trace.ts
    │       └── preview.ts

# 八、开发强约束

1.  模板变量统一使用 `{table_name}.{field_name}`，禁止使用 `data.field_name`。
2.  主表只负责批量生成驱动，不作为模板变量别名。
3.  MVP不实现审核写入API。
4.  MVP不实现驳回、备注、复核。
5.  MVP不实现RAG。
6.  MVP不向Word写入溯源批注。
7.  最终Word必须保持干净。
8.  trace和preview必须在生成阶段同步产生。
9.  Web预览基于preview.json，不依赖前端解析docx。
10. 下载接口只能下载当前任务output目录下的docx或生成的zip。
