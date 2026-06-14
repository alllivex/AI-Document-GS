from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd

from app.models.enums import DataType


def format_display_value(value: Any, field_schema: Any | None = None) -> str:
    if is_missing_value(value):
        return ""

    data_type = _get_data_type(field_schema)
    display_format = _get_display_format(field_schema)

    if data_type == DataType.DATE.value:
        return _format_date(value)
    if data_type == DataType.DATETIME.value:
        return _format_datetime(value)
    if data_type == DataType.PERCENT.value:
        return _format_percent(value, display_format)
    if data_type == DataType.AMOUNT.value:
        return _format_decimal(value, display_format, default_places=2)
    if data_type == DataType.INTEGER.value:
        return _format_integer(value)
    if data_type == DataType.NUMBER.value:
        return _format_decimal(value, display_format, default_places=None)
    if data_type == DataType.BOOLEAN.value:
        return _format_boolean(value)

    if isinstance(value, pd.Timestamp):
        return _format_datetime(value.to_pydatetime())
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, date):
        return _format_date(value)
    return str(value)


def normalize_raw_value(value: Any) -> str | bool | int | float | None:
    if is_missing_value(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool | str | int | float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _get_data_type(field_schema: Any | None) -> str:
    if field_schema is None:
        return DataType.STRING.value
    data_type = getattr(field_schema, "data_type", DataType.STRING.value)
    return getattr(data_type, "value", data_type)


def _get_display_format(field_schema: Any | None) -> str:
    if field_schema is None:
        return ""
    return getattr(field_schema, "display_format", "") or ""


def _format_date(value: Any) -> str:
    parsed = _to_datetime(value)
    if parsed is None:
        return str(value)
    return parsed.strftime("%Y-%m-%d")


def _format_datetime(value: Any) -> str:
    parsed = _to_datetime(value)
    if parsed is None:
        return str(value)
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _format_percent(value: Any, display_format: str) -> str:
    number = _to_decimal(value)
    if number is None:
        return str(value)
    places = _extract_places(display_format, default=2)
    return f"{number * Decimal('100'):.{places}f}%"


def _format_decimal(value: Any, display_format: str, default_places: int | None) -> str:
    number = _to_decimal(value)
    if number is None:
        return str(value)

    places = _extract_places(display_format, default=default_places)
    if places is None:
        normalized = number.normalize()
        return format(normalized, "f")
    return f"{number:.{places}f}"


def _format_integer(value: Any) -> str:
    number = _to_decimal(value)
    if number is None:
        return str(value)
    return str(int(number))


def _format_boolean(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return "true"
        if normalized in {"false", "0", "no", "n"}:
            return "false"
    return "true" if bool(value) else "false"


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        parsed = pd.to_datetime(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _to_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _extract_places(display_format: str, default: int | None) -> int | None:
    if not display_format:
        return default
    suffix = display_format.rsplit("_", maxsplit=1)[-1]
    if suffix.isdigit():
        return int(suffix)
    return default
