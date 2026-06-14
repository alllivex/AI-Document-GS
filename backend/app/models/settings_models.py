from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.models.enums import DataType
from app.models.common import ContractModel


class SettingsHealth(ContractModel):
    status: Literal["ok"]


class TemplateFileRecord(ContractModel):
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    original_filename: str
    template_path: str
    description: str = ""
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class EntitySchemaFieldRecord(ContractModel):
    id: int = Field(ge=1)
    table_name: str
    table_name_cn: str = ""
    field_name: str
    field_name_cn: str = ""
    data_type: DataType = DataType.STRING
    is_primary_key: bool = False
    required: bool = False
    display_format: str = ""
    description: str = ""
    is_active: bool = True


class EntitySchemaImportSummary(ContractModel):
    total_rows: int = Field(ge=0)
    create_count: int = Field(ge=0)
    update_count: int = Field(ge=0)
    skip_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)


class EntitySchemaImportItem(ContractModel):
    row_number: int = Field(ge=1)
    action: Literal["create", "update", "skip", "error"]
    level: Literal["info", "warning", "error"]
    message: str


class EntitySchemaImportPreview(ContractModel):
    import_id: str
    summary: EntitySchemaImportSummary
    items: list[EntitySchemaImportItem]
    can_commit: bool


class EntitySchemaImportCommitRequest(ContractModel):
    import_id: str
    mode: Literal["upsert"] = "upsert"


class TemplateRelationRecord(ContractModel):
    id: int = Field(ge=1)
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    table_name: str
    table_name_cn: str = ""
    role: Literal["main", "aux"]
    relation_type: Literal["main", "one_to_one", "one_to_many"]
    main_join_key: str = ""
    table_join_key: str = ""
    required: bool = True
    description: str = ""


class TemplateRelationImportSummary(ContractModel):
    total_rows: int = Field(ge=0)
    create_count: int = Field(ge=0)
    update_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)


class TemplateRelationImportItem(ContractModel):
    row_number: int = Field(ge=1)
    action: Literal["create", "update", "skip", "error"]
    level: Literal["info", "warning", "error"]
    message: str


class TemplateRelationImportPreview(ContractModel):
    import_id: str
    summary: TemplateRelationImportSummary
    items: list[TemplateRelationImportItem]
    can_commit: bool


class TemplateRelationImportCommitRequest(ContractModel):
    import_id: str
    mode: Literal["upsert"] = "upsert"


class AIConfigResponse(ContractModel):
    provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: int = Field(default=60, ge=1)
    api_key_configured: bool = False
    api_key_source: Literal["env", "db", "none"] = "none"
    is_active: bool = True
    status: Literal["available", "unavailable"] = "unavailable"


class AIConfigUpdateRequest(ContractModel):
    provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = Field(default=0.2, ge=0, le=2)
    timeout_seconds: int = Field(default=60, ge=1, le=600)
    is_active: bool = True


class AIConfigTestResult(ContractModel):
    status: Literal["success", "failed"]
    message: str
