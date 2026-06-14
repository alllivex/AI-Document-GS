from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.enums import DataType
from app.models.template_models import FieldDefinition

REQUIRED_SCHEMA_COLUMNS = {"table_name", "field_name", "is_primary_key"}


@dataclass(frozen=True)
class TranslationMaps:
    table_en_to_cn: dict[str, str]
    table_cn_to_en: dict[str, str]
    field_en_to_cn: dict[tuple[str, str], str]
    field_cn_to_en: dict[tuple[str, str], str]
    field_en_to_cn_by_table: dict[str, dict[str, str]]
    field_cn_to_en_by_table: dict[str, dict[str, str]]


def load_entity_schema(schema_xlsx: Path) -> list[FieldDefinition]:
    if not schema_xlsx.exists():
        raise FileNotFoundError(f"entity schema file not found: {schema_xlsx}")

    dataframe = pd.read_excel(schema_xlsx, sheet_name=0)
    _require_columns(dataframe, REQUIRED_SCHEMA_COLUMNS, "entity schema")
    normalized = _normalize_schema_dataframe(dataframe)
    fields = [_row_to_field_definition(row) for row in normalized.to_dict(orient="records")]
    validate_primary_keys(fields)
    return fields


def build_translation_maps(fields: list[FieldDefinition]) -> TranslationMaps:
    table_en_to_cn: dict[str, str] = {}
    table_cn_to_en: dict[str, str] = {}
    field_en_to_cn: dict[tuple[str, str], str] = {}
    field_cn_to_en: dict[tuple[str, str], str] = {}
    field_en_to_cn_by_table: dict[str, dict[str, str]] = {}
    field_cn_to_en_by_table: dict[str, dict[str, str]] = {}

    for field in fields:
        if field.table_name_cn:
            table_en_to_cn[field.table_name] = field.table_name_cn
            table_cn_to_en[field.table_name_cn] = field.table_name
        if field.field_name_cn:
            field_en_to_cn[(field.table_name, field.field_name)] = field.field_name_cn
            field_en_to_cn_by_table.setdefault(field.table_name, {})[field.field_name] = field.field_name_cn
            if field.table_name_cn:
                field_cn_to_en[(field.table_name_cn, field.field_name_cn)] = field.field_name
                field_cn_to_en_by_table.setdefault(field.table_name_cn, {})[field.field_name_cn] = field.field_name

    return TranslationMaps(
        table_en_to_cn=table_en_to_cn,
        table_cn_to_en=table_cn_to_en,
        field_en_to_cn=field_en_to_cn,
        field_cn_to_en=field_cn_to_en,
        field_en_to_cn_by_table=field_en_to_cn_by_table,
        field_cn_to_en_by_table=field_cn_to_en_by_table,
    )


def validate_primary_keys(fields: list[FieldDefinition]) -> None:
    primary_key_counts: dict[str, int] = {}
    table_names = {field.table_name for field in fields}
    for field in fields:
        if field.is_primary_key:
            primary_key_counts[field.table_name] = primary_key_counts.get(field.table_name, 0) + 1

    invalid_tables = [
        table_name
        for table_name in sorted(table_names)
        if primary_key_counts.get(table_name, 0) != 1
    ]
    if invalid_tables:
        raise ValueError(f"each table must have exactly one primary key: {', '.join(invalid_tables)}")


def _require_columns(dataframe: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def _normalize_schema_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = dataframe.copy()
    normalized = normalized.rename(
        columns={
            "table_name_chinese": "table_name_cn",
            "field_name_chinese": "field_name_cn",
        }
    )
    defaults: dict[str, Any] = {
        "table_name_cn": "",
        "field_name_cn": "",
        "data_type": DataType.STRING.value,
        "required": False,
        "display_format": "",
        "description": "",
    }
    for column, default in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default
    return normalized


def _row_to_field_definition(row: dict[str, Any]) -> FieldDefinition:
    return FieldDefinition(
        table_name=_clean_text(row["table_name"]),
        table_name_cn=_clean_text(row.get("table_name_cn", "")),
        field_name=_clean_text(row["field_name"]),
        field_name_cn=_clean_text(row.get("field_name_cn", "")),
        data_type=_clean_data_type(row.get("data_type", DataType.STRING.value)),
        is_primary_key=_to_bool(row.get("is_primary_key", False)),
        required=_to_bool(row.get("required", False)),
        display_format=_clean_text(row.get("display_format", "")),
        description=_clean_text(row.get("description", "")),
    )


def _clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_data_type(value: Any) -> DataType:
    cleaned = _clean_text(value) or DataType.STRING.value
    try:
        return DataType(cleaned)
    except ValueError as exc:
        raise ValueError(f"unsupported data type: {cleaned}") from exc


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}
