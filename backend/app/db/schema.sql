PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    template_name TEXT NOT NULL,
    template_file TEXT NOT NULL,
    template_path TEXT NOT NULL,
    main_table TEXT NOT NULL,
    output_name_pattern TEXT NOT NULL DEFAULT '{template_name}_{primary_key_value}.docx',
    ai_enabled_default INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_template_file
ON templates(template_file);

CREATE INDEX IF NOT EXISTS idx_templates_main_table
ON templates(main_table);

CREATE INDEX IF NOT EXISTS idx_templates_active
ON templates(is_active);

CREATE TABLE IF NOT EXISTS template_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    table_name_cn TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL CHECK (role IN ('main', 'aux')),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('main', 'one_to_one', 'one_to_many')),
    main_join_key TEXT NOT NULL DEFAULT '',
    table_join_key TEXT NOT NULL DEFAULT '',
    required INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_template_tables_template_id
ON template_tables(template_id);

CREATE INDEX IF NOT EXISTS idx_template_tables_table_name
ON template_tables(table_name);

CREATE UNIQUE INDEX IF NOT EXISTS idx_template_tables_unique
ON template_tables(template_id, table_name);

CREATE TABLE IF NOT EXISTS fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    table_name_cn TEXT NOT NULL DEFAULT '',
    field_name TEXT NOT NULL,
    field_name_cn TEXT NOT NULL DEFAULT '',
    data_type TEXT NOT NULL DEFAULT 'string'
        CHECK (data_type IN ('string', 'number', 'integer', 'date', 'datetime', 'percent', 'boolean', 'amount')),
    is_primary_key INTEGER NOT NULL DEFAULT 0,
    required INTEGER NOT NULL DEFAULT 0,
    display_format TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_fields_unique
ON fields(table_name, field_name);

CREATE INDEX IF NOT EXISTS idx_fields_table_name
ON fields(table_name);

CREATE INDEX IF NOT EXISTS idx_fields_primary_key
ON fields(table_name, is_primary_key);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    template_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
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
    ai_enabled INTEGER NOT NULL DEFAULT 1,
    main_table TEXT NOT NULL,
    primary_key_field TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    task_dir TEXT NOT NULL,
    validation_report_path TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status
ON tasks(status);

CREATE INDEX IF NOT EXISTS idx_tasks_template_id
ON tasks(template_id);

CREATE INDEX IF NOT EXISTS idx_tasks_created_at
ON tasks(created_at);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    file_ext TEXT NOT NULL DEFAULT '.xlsx',
    row_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    checksum TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_uploaded_files_task_id
ON uploaded_files(task_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_uploaded_files_task_table
ON uploaded_files(task_id, table_name);

CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    template_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
    primary_key_value TEXT NOT NULL,
    output_filename TEXT NOT NULL,
    output_path TEXT NOT NULL,
    trace_filename TEXT NOT NULL,
    trace_path TEXT NOT NULL,
    preview_filename TEXT NOT NULL,
    preview_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'success', 'failed', 'ai_partial_failed')),
    ai_status TEXT NOT NULL DEFAULT 'not_used'
        CHECK (ai_status IN ('not_used', 'success', 'partial_failed', 'failed')),
    trace_count INTEGER NOT NULL DEFAULT 0,
    ai_block_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

CREATE INDEX IF NOT EXISTS idx_documents_task_id
ON documents(task_id);

CREATE INDEX IF NOT EXISTS idx_documents_template_id
ON documents(template_id);

CREATE INDEX IF NOT EXISTS idx_documents_primary_key_value
ON documents(primary_key_value);

CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_task_pk
ON documents(task_id, primary_key_value);

CREATE TABLE IF NOT EXISTS generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    doc_id TEXT NOT NULL DEFAULT '',
    level TEXT NOT NULL CHECK (level IN ('debug', 'info', 'warning', 'error')),
    stage TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_generation_logs_task_id
ON generation_logs(task_id);

CREATE INDEX IF NOT EXISTS idx_generation_logs_doc_id
ON generation_logs(doc_id);

CREATE INDEX IF NOT EXISTS idx_generation_logs_level
ON generation_logs(level);

CREATE INDEX IF NOT EXISTS idx_generation_logs_created_at
ON generation_logs(created_at);

CREATE TABLE IF NOT EXISTS validation_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'passed_with_warnings')),
    report_path TEXT NOT NULL,
    error_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    info_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_reports_task_id
ON validation_reports(task_id);

CREATE INDEX IF NOT EXISTS idx_validation_reports_status
ON validation_reports(status);
