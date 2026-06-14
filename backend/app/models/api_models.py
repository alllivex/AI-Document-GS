from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import Field

from app.models.common import ContractModel

T = TypeVar("T")


class ApiErrorDetail(ContractModel):
    code: str
    message: str
    detail: Any | None = None


class ApiSuccess(ContractModel, Generic[T]):
    success: Literal[True] = True
    data: T
    request_id: str
    timestamp: datetime


class ApiError(ContractModel):
    success: Literal[False] = False
    error: ApiErrorDetail
    request_id: str
    timestamp: datetime


class ApiResponse(ContractModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiErrorDetail | None = None
    request_id: str
    timestamp: datetime


class PagedResponse(ContractModel, Generic[T]):
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
