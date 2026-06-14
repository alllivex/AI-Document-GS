from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import ContractModel
from app.models.enums import AIStatus, DocumentStatus, TaskStatus
from app.models.file_models import UploadedFileMeta
from app.models.template_models import RequiredTable


class OutputSummary(ContractModel):
    total_rows: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    document_ids: list[str] = Field(default_factory=list)


class TaskPaths(ContractModel):
    task_dir: str
    data_dir: str
    output_dir: str
    validation_dir: str
    logs_dir: str


class TaskMeta(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    task_name: str
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    ai_enabled: bool
    status: TaskStatus
    main_table: str
    main_table_cn: str = ""
    primary_key_field: str
    required_tables: list[RequiredTable]
    uploaded_files: list[UploadedFileMeta] = Field(default_factory=list)
    output_summary: OutputSummary
    paths: TaskPaths
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskRecord(ContractModel):
    task_id: str
    task_name: str
    template_id: int = Field(ge=1)
    template_name: str
    status: TaskStatus
    ai_enabled: bool = True
    main_table: str
    primary_key_field: str
    total_rows: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    task_dir: str
    validation_report_path: str = ""
    error_message: str = ""
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskListItem(TaskRecord):
    pass


class DocumentRecord(ContractModel):
    doc_id: str
    task_id: str
    template_id: int = Field(ge=1)
    template_name: str
    primary_key_value: str
    output_filename: str
    output_path: str
    trace_filename: str
    trace_path: str
    preview_filename: str
    preview_path: str
    status: DocumentStatus = DocumentStatus.PENDING
    ai_status: AIStatus = AIStatus.NOT_USED
    trace_count: int = Field(default=0, ge=0)
    ai_block_count: int = Field(default=0, ge=0)
    error_message: str = ""
    created_at: datetime
    updated_at: datetime


class TaskOutputsResponse(ContractModel):
    task_id: str
    items: list[DocumentRecord]
    total: int = Field(ge=0)
