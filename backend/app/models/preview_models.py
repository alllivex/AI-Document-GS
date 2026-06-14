from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from app.models.common import ContractModel


class PreviewRunStyle(ContractModel):
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None


class PreviewRun(ContractModel):
    text: str
    trace_id: str | None = None
    ai_block_id: str | None = None
    style: PreviewRunStyle | None = None


class PreviewTableCell(ContractModel):
    text: str
    trace_id: str | None = None
    ai_block_id: str | None = None


class PreviewHeadingBlock(ContractModel):
    type: Literal["heading"] = "heading"
    block_id: str
    level: Literal[1, 2, 3, 4, 5, 6]
    text: str


class PreviewParagraphBlock(ContractModel):
    type: Literal["paragraph"] = "paragraph"
    block_id: str
    runs: list[PreviewRun]


class PreviewTableBlock(ContractModel):
    type: Literal["table"] = "table"
    block_id: str
    headers: list[PreviewTableCell]
    rows: list[list[PreviewTableCell]]


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
