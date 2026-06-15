from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from app.models.common import ContractModel


class PreviewRunStyle(ContractModel):
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    alignment: str | None = None
    color: str | None = None
    background_color: str | None = None
    font_size_pt: float | None = None


class PreviewRun(ContractModel):
    text: str
    trace_id: str | None = None
    trace_kind: Literal["field", "condition", "loop", "ai"] | None = None
    ai_block_id: str | None = None
    style: PreviewRunStyle | None = None


class PreviewTableCell(ContractModel):
    text: str
    trace_id: str | None = None
    trace_kind: Literal["field", "condition", "loop", "ai"] | None = None
    ai_block_id: str | None = None
    runs: list[PreviewRun] | None = None
    colspan: int = Field(default=1, ge=1)
    rowspan: int = Field(default=1, ge=1)
    style: PreviewRunStyle | None = None
    width_px: float | None = None


class PreviewHeadingBlock(ContractModel):
    type: Literal["heading"] = "heading"
    block_id: str
    level: Literal[1, 2, 3, 4, 5, 6]
    text: str


class PreviewParagraphBlock(ContractModel):
    type: Literal["paragraph"] = "paragraph"
    block_id: str
    block_trace_id: str | None = None
    block_trace_kind: Literal["field", "condition", "loop", "ai"] | None = None
    runs: list[PreviewRun]
    style: PreviewRunStyle | None = None


class PreviewTableBlock(ContractModel):
    type: Literal["table"] = "table"
    block_id: str
    block_trace_id: str | None = None
    block_trace_kind: Literal["field", "condition", "loop", "ai"] | None = None
    headers: list[PreviewTableCell]
    rows: list[list[PreviewTableCell]]
    style: PreviewRunStyle | None = None
    width_px: float | None = None


PreviewBlock = Annotated[
    PreviewHeadingBlock | PreviewParagraphBlock | PreviewTableBlock,
    Field(discriminator="type"),
]


class PreviewFile(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    doc_id: str
    task_id: str
    title: str
    output_file: str
    primary_key_value: str
    blocks: list[PreviewBlock]
    created_at: datetime
