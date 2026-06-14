from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.common import ContractModel
from app.models.enums import AIBlockStatus, DataType, RelationType
from app.models.file_models import SourceFileInfo

RawTraceValue = str | bool | int | float | None


class TraceItem(ContractModel):
    trace_id: str
    var_path: str
    table_name: str
    table_name_cn: str = ""
    field_name: str
    field_name_cn: str = ""
    source_file: str
    source_file_path: str
    pk_field: str
    pk_value: str
    row_index: int = Field(ge=0)
    excel_row_number: int = Field(ge=1)
    column_index: int | None = Field(default=None, ge=0)
    excel_column_letter: str | None = None
    raw_value: RawTraceValue
    display_value: str
    value_type: DataType
    display_format: str = ""
    occurrence_index: int = Field(ge=0)
    source_relation_type: RelationType
    created_at: datetime


class AIBlockTrace(ContractModel):
    block_id: str
    marker: str
    status: AIBlockStatus
    prompt_template: str
    prompt_rendered: str
    model: str
    input_variables: list[str]
    generated_text: str = ""
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TraceStatistics(ContractModel):
    trace_item_count: int = Field(ge=0)
    ai_block_count: int = Field(ge=0)
    source_file_count: int = Field(ge=0)
    table_count: int = Field(ge=0)


class TraceFile(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    doc_id: str
    task_id: str
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    output_file: str
    output_path: str
    main_table: str
    main_table_cn: str = ""
    primary_key_field: str
    primary_key_value: str
    generated_at: datetime
    source_files: list[SourceFileInfo]
    trace_items: list[TraceItem]
    ai_blocks: list[AIBlockTrace]
    statistics: TraceStatistics
