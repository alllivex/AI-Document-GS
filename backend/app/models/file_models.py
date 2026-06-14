from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.common import ContractModel
from app.models.enums import DataType


class UploadedFileMeta(ContractModel):
    table_name: str
    original_filename: str
    stored_filename: str
    path: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    uploaded_at: datetime


class UploadedFileRecord(UploadedFileMeta):
    task_id: str
    file_path: str
    file_size: int = Field(default=0, ge=0)
    file_ext: str = ".xlsx"
    checksum: str = ""


class SourceFileInfo(ContractModel):
    table_name: str
    table_name_cn: str = ""
    filename: str
    path: str
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)


class SourceRowColumn(ContractModel):
    field_name: str
    field_name_cn: str = ""
    excel_column_letter: str
    data_type: DataType = DataType.STRING


class SourceRowResponse(ContractModel):
    trace_id: str
    table_name: str
    table_name_cn: str = ""
    source_file: str
    excel_row_number: int = Field(ge=1)
    highlight_field: str
    columns: list[SourceRowColumn]
    row: dict[str, str | int | float | bool | None]
