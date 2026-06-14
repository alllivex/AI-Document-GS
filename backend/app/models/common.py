from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0"
SchemaVersion = Literal["1.0"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True, validate_default=True)


class TimestampedModel(ContractModel):
    created_at: datetime
    updated_at: datetime


class Pagination(ContractModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1)
    total: int = Field(default=0, ge=0)
