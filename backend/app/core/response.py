from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    error: ApiErrorDetail | None = None
    request_id: str
    timestamp: datetime


def new_request_id() -> str:
    return uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


def success_response(data: Any, request_id: str | None = None) -> dict[str, Any]:
    return ApiResponse(
        success=True,
        data=data,
        request_id=request_id or new_request_id(),
        timestamp=utc_now(),
    ).model_dump(mode="json")


def error_response(
    code: str,
    message: str,
    status_details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return ApiResponse(
        success=False,
        error=ApiErrorDetail(code=code, message=message, details=status_details or {}),
        request_id=request_id or new_request_id(),
        timestamp=utc_now(),
    ).model_dump(mode="json")
