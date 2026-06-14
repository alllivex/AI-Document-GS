from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.models.common import ContractModel
from app.models.enums import AIBlockStatus, DataType, RelationType
from app.models.file_models import SourceFileInfo

RawTraceValue = str | bool | int | float | None
TraceKind = Literal["field", "condition", "loop", "ai"]
HighlightReason = Literal["clicked", "used_in_condition", "used_in_loop", "none"]


class TraceItem(ContractModel):
    trace_id: str
    original_var_path: str | None = None
    canonical_var_path: str = ""
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

    @model_validator(mode="after")
    def fill_variable_paths(self) -> "TraceItem":
        if not self.canonical_var_path:
            self.canonical_var_path = self.var_path
        if self.original_var_path is None:
            self.original_var_path = self.var_path
        return self


class SourceRecordField(ContractModel):
    field_name: str
    field_name_cn: str = ""
    raw_value: RawTraceValue
    display_value: str
    value_type: str
    excel_column_letter: str | None = None
    is_highlighted: bool = False
    highlight_reason: HighlightReason = "none"


class SourceRecordView(ContractModel):
    table_name: str
    table_name_cn: str = ""
    source_file: str
    row_index: int = Field(ge=0)
    excel_row_number: int = Field(ge=1)
    relation_type: RelationType
    fields: list[SourceRecordField]


class BaseTraceDetail(ContractModel):
    trace_id: str
    trace_kind: TraceKind
    task_id: str
    doc_id: str
    primary_key_value: str


class FieldTraceDetail(BaseTraceDetail):
    trace_kind: Literal["field"] = "field"
    original_var_path: str | None = None
    canonical_var_path: str = ""
    var_path: str
    table_name: str
    table_name_cn: str = ""
    field_name: str
    field_name_cn: str = ""
    source_record: SourceRecordView

    @model_validator(mode="after")
    def fill_variable_paths(self) -> "FieldTraceDetail":
        if not self.canonical_var_path:
            self.canonical_var_path = self.var_path
        if self.original_var_path is None:
            self.original_var_path = self.var_path
        return self


class ConditionTraceDetail(BaseTraceDetail):
    trace_kind: Literal["condition"] = "condition"
    expression: str
    used_variables: list[str]
    evaluated_result: bool
    selected_branch: Literal["if", "else"]
    expected_output_text: str
    actual_output_text: str
    is_consistent: bool
    source_records: list[SourceRecordView]


class LoopTraceDetail(BaseTraceDetail):
    trace_kind: Literal["loop"] = "loop"
    table_name: str
    table_name_cn: str = ""
    loop_alias: str
    used_fields: list[str]
    matched_row_count: int = Field(ge=0)
    source_records: list[SourceRecordView]


class AIInputVariable(ContractModel):
    original_var_path: str | None = None
    canonical_var_path: str = ""
    var_path: str
    table_name: str
    table_name_cn: str = ""
    field_name: str
    field_name_cn: str = ""
    raw_value: RawTraceValue
    display_value: str
    trace_id: str | None = None
    source_file: str = ""
    excel_row_number: int | None = None
    excel_column_letter: str | None = None

    @model_validator(mode="after")
    def fill_variable_paths(self) -> "AIInputVariable":
        if not self.canonical_var_path:
            self.canonical_var_path = self.var_path
        if self.original_var_path is None:
            self.original_var_path = self.var_path
        return self


class KnowledgeReference(ContractModel):
    kb_name: str
    retrieval_enabled: bool = False
    chunk_id: str | None = None
    doc_name: str | None = None
    score: float | None = None
    excerpt: str | None = None


class AITraceDetail(BaseTraceDetail):
    trace_kind: Literal["ai"] = "ai"
    block_id: str
    marker: str
    status: Literal["success", "failed", "skipped"]
    original_block_text: str
    prompt_template: str
    prompt_rendered: str
    model: str
    temperature: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    input_variables: list[AIInputVariable] = Field(default_factory=list)
    knowledge_refs: list[KnowledgeReference] = Field(default_factory=list)
    generated_text: str = ""
    error_message: str = ""


TraceDetail = Annotated[
    FieldTraceDetail | ConditionTraceDetail | LoopTraceDetail | AITraceDetail,
    Field(discriminator="trace_kind"),
]


class AIBlockTrace(ContractModel):
    block_id: str
    marker: str
    status: AIBlockStatus
    original_block_text: str = ""
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
    condition_traces: list[ConditionTraceDetail] = Field(default_factory=list)
    loop_traces: list[LoopTraceDetail] = Field(default_factory=list)
    ai_traces: list[AITraceDetail] = Field(default_factory=list)
    ai_blocks: list[AIBlockTrace]
    statistics: TraceStatistics
