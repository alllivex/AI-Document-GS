from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.common import ContractModel
from app.models.enums import DataType, RelationType, TableRole


class FieldDefinition(ContractModel):
    table_name: str
    table_name_cn: str = ""
    field_name: str
    field_name_cn: str = ""
    data_type: DataType = DataType.STRING
    is_primary_key: bool = False
    required: bool = False
    display_format: str = ""
    description: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RequiredTable(ContractModel):
    table_name: str
    table_name_cn: str = ""
    role: TableRole
    relation_type: RelationType
    main_join_key: str = ""
    table_join_key: str = ""
    required: bool = True


class TemplateInfo(ContractModel):
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    template_path: str
    main_table: str
    output_name_pattern: str = "{template_name}_{primary_key_value}.docx"
    ai_enabled_default: bool = True
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class TemplateRequirements(ContractModel):
    template_id: int = Field(ge=1)
    template_name: str
    template_file: str
    template_path: str
    main_table: str
    primary_key_field: str
    required_tables: list[RequiredTable]
    fields: list[FieldDefinition] = Field(default_factory=list)
