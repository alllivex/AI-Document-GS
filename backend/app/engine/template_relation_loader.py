from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from app.models.common import ContractModel
from app.models.enums import RelationType, TableRole

REQUIRED_RELATION_COLUMNS = {"template_id", "template_name", "template_file", "table_name", "role"}


class TemplateRelationDefinition(ContractModel):
    template_id: int
    template_name: str
    template_file: str
    table_name: str
    table_name_cn: str = ""
    role: TableRole
    relation_type: RelationType
    main_join_key: str = ""
    table_join_key: str = ""
    required: bool = True
    sort_order: int = 0
    description: str = ""


@dataclass(frozen=True)
class TemplateConfig:
    template_id: int
    template_name: str
    template_file: str
    main_table: str


def load_template_relation(relation_xlsx: Path) -> list[TemplateRelationDefinition]:
    if not relation_xlsx.exists():
        raise FileNotFoundError(f"template relation file not found: {relation_xlsx}")

    dataframe = pd.read_excel(relation_xlsx, sheet_name=0)
    _require_columns(dataframe, REQUIRED_RELATION_COLUMNS, "template relation")
    normalized = _normalize_relation_dataframe(dataframe)
    relations = [_row_to_relation_definition(row) for row in normalized.to_dict(orient="records")]
    validate_template_main_tables(relations)
    return relations


def validate_template_main_tables(relations: list[TemplateRelationDefinition]) -> None:
    template_ids = {relation.template_id for relation in relations}
    invalid_templates: list[str] = []
    for template_id in sorted(template_ids):
        main_count = sum(1 for relation in relations if relation.template_id == template_id and relation.role == TableRole.MAIN)
        if main_count != 1:
            invalid_templates.append(str(template_id))
    if invalid_templates:
        raise ValueError(f"each template must have exactly one main table: {', '.join(invalid_templates)}")


def get_template_configs(relations: list[TemplateRelationDefinition]) -> list[TemplateConfig]:
    configs: list[TemplateConfig] = []
    for relation in relations:
        if relation.role == TableRole.MAIN:
            configs.append(
                TemplateConfig(
                    template_id=relation.template_id,
                    template_name=relation.template_name,
                    template_file=relation.template_file,
                    main_table=relation.table_name,
                )
            )
    return sorted(configs, key=lambda item: item.template_id)


def _require_columns(dataframe: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def _normalize_relation_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    normalized = dataframe.copy()
    normalized = normalized.rename(columns={"table_name_chinese": "table_name_cn"})
    defaults: dict[str, Any] = {
        "table_name_cn": "",
        "relation_type": "",
        "main_join_key": "",
        "table_join_key": "",
        "required": True,
        "sort_order": 0,
        "description": "",
    }
    for column, default in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default
    return normalized


def _row_to_relation_definition(row: dict[str, Any]) -> TemplateRelationDefinition:
    role = _clean_role(row["role"])
    relation_type = _clean_relation_type(row.get("relation_type", ""), role)
    return TemplateRelationDefinition(
        template_id=int(row["template_id"]),
        template_name=_clean_text(row["template_name"]),
        template_file=_clean_text(row["template_file"]),
        table_name=_clean_text(row["table_name"]),
        table_name_cn=_clean_text(row.get("table_name_cn", "")),
        role=role,
        relation_type=relation_type,
        main_join_key=_clean_text(row.get("main_join_key", "")),
        table_join_key=_clean_text(row.get("table_join_key", "")),
        required=_to_bool(row.get("required", True)),
        sort_order=_to_int(row.get("sort_order", 0)),
        description=_clean_text(row.get("description", "")),
    )


def _clean_role(value: Any) -> TableRole:
    cleaned = _clean_text(value).lower()
    try:
        return TableRole(cleaned)
    except ValueError as exc:
        raise ValueError(f"unsupported table role: {cleaned}") from exc


def _clean_relation_type(value: Any, role: TableRole) -> RelationType:
    cleaned = _clean_text(value).lower()
    if not cleaned:
        return RelationType.MAIN if role == TableRole.MAIN else RelationType.ONE_TO_MANY
    try:
        return RelationType(cleaned)
    except ValueError as exc:
        raise ValueError(f"unsupported relation type: {cleaned}") from exc


def _clean_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_bool(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def _to_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    if value == "":
        return 0
    return int(value)
