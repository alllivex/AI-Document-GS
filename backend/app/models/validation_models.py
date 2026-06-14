from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.models.common import ContractModel
from app.models.enums import ValidationLevel, ValidationStatus


class ValidationSummary(ContractModel):
    error_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    info_count: int = Field(default=0, ge=0)


class ValidationItem(ContractModel):
    level: ValidationLevel
    code: str
    message: str
    table_name: str | None = None
    field_name: str | None = None
    template_id: int | None = None
    template_file: str | None = None
    suggestion: str | None = None
    detail: dict[str, Any] | None = None


class ValidationReport(ContractModel):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str
    status: ValidationStatus
    summary: ValidationSummary
    items: list[ValidationItem]
    created_at: datetime


class ValidateTaskRequest(ContractModel):
    force: bool = False


class ValidateTaskResponse(ContractModel):
    task_id: str
    status: ValidationStatus
    report_path: str
    summary: ValidationSummary
    items: list[ValidationItem]
