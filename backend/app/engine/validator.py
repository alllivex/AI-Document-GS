from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import AppSettings
from app.engine.data_loader import LoadedTable
from app.engine.template_parser import analyze_template_variables
from app.engine.validation_report_writer import write_validation_report
from app.models.enums import RelationType, TableRole, ValidationLevel, ValidationStatus
from app.models.template_models import FieldDefinition, RequiredTable, TemplateRequirements
from app.models.validation_models import ValidationItem, ValidationReport, ValidationSummary


def validate_task(
    task_id: str,
    template_requirements: TemplateRequirements,
    loaded_tables: Mapping[str, LoadedTable] | Any,
    template_path: Path,
    task_dir: Path | None = None,
    settings: AppSettings | None = None,
) -> ValidationReport:
    tables = _coerce_loaded_tables(loaded_tables)
    items: list[ValidationItem] = []

    if not template_path.exists():
        items.append(
            _error(
                "template_file_missing",
                f"Template file not found: {template_path}",
                template_requirements,
                detail={"template_path": str(template_path)},
            )
        )

    _validate_required_tables(template_requirements, tables, items)
    _validate_required_fields(template_requirements, tables, items)
    _validate_main_primary_key(template_requirements, tables, items)
    _validate_one_to_one_relations(template_requirements, tables, items)
    _validate_template_references(template_requirements, tables, template_path, items)

    report = _build_report(task_id, items)
    write_validation_report(task_id, report, task_dir=task_dir, settings=settings)
    return report


def _validate_required_tables(
    requirements: TemplateRequirements,
    tables: Mapping[str, LoadedTable],
    items: list[ValidationItem],
) -> None:
    for required_table in requirements.required_tables:
        if required_table.table_name in tables:
            continue

        if required_table.required:
            items.append(
                _error(
                    "missing_required_table",
                    f"Required Excel table is missing: {required_table.table_name}.xlsx",
                    requirements,
                    table_name=required_table.table_name,
                    suggestion=f"Upload tasks/{{task_id}}/data/{required_table.table_name}.xlsx before validation.",
                )
            )
        else:
            items.append(
                _warning(
                    "missing_optional_table",
                    f"Optional Excel table is missing: {required_table.table_name}.xlsx",
                    requirements,
                    table_name=required_table.table_name,
                    suggestion="Upload this file if the template needs data from the optional table.",
                )
            )


def _validate_required_fields(
    requirements: TemplateRequirements,
    tables: Mapping[str, LoadedTable],
    items: list[ValidationItem],
) -> None:
    for field in requirements.fields:
        if not field.required:
            continue
        table = tables.get(field.table_name)
        if table is None:
            continue
        if field.field_name not in table.columns:
            items.append(
                _error(
                    "missing_required_field",
                    f"Required field is missing: {field.table_name}.{field.field_name}",
                    requirements,
                    table_name=field.table_name,
                    field_name=field.field_name,
                    suggestion=f"Add column '{field.field_name}' to {field.table_name}.xlsx.",
                )
            )


def _validate_main_primary_key(
    requirements: TemplateRequirements,
    tables: Mapping[str, LoadedTable],
    items: list[ValidationItem],
) -> None:
    main_table = tables.get(requirements.main_table)
    if main_table is None:
        return

    primary_key = requirements.primary_key_field
    if primary_key not in main_table.columns:
        items.append(
            _error(
                "missing_primary_key_field",
                f"Primary key field is missing: {requirements.main_table}.{primary_key}",
                requirements,
                table_name=requirements.main_table,
                field_name=primary_key,
                suggestion=f"Add primary key column '{primary_key}' to {requirements.main_table}.xlsx.",
            )
        )
        return

    series = main_table.dataframe[primary_key]
    empty_row_numbers = [
        _excel_row_number(index)
        for index, value in series.items()
        if _is_empty_cell(value)
    ]
    if empty_row_numbers:
        items.append(
            _error(
                "empty_primary_key",
                f"Primary key field contains empty values: {requirements.main_table}.{primary_key}",
                requirements,
                table_name=requirements.main_table,
                field_name=primary_key,
                detail={"excel_row_numbers": empty_row_numbers},
                suggestion="Fill every primary key value before generation.",
            )
        )

    duplicated_values = _duplicated_non_empty_values(series)
    if duplicated_values:
        items.append(
            _error(
                "duplicated_primary_key",
                f"Primary key field contains duplicated values: {requirements.main_table}.{primary_key}",
                requirements,
                table_name=requirements.main_table,
                field_name=primary_key,
                detail={"duplicated_values": duplicated_values},
                suggestion="Keep primary key values unique in the main table.",
            )
        )


def _validate_one_to_one_relations(
    requirements: TemplateRequirements,
    tables: Mapping[str, LoadedTable],
    items: list[ValidationItem],
) -> None:
    main_table = tables.get(requirements.main_table)
    main_key_values = _non_empty_key_values(main_table, requirements.primary_key_field) if main_table else set()

    for table_requirement in requirements.required_tables:
        if table_requirement.role == TableRole.MAIN or table_requirement.relation_type != RelationType.ONE_TO_ONE:
            continue

        table = tables.get(table_requirement.table_name)
        if table is None:
            continue

        join_key = _join_key_for(table_requirement, requirements)
        if join_key not in table.columns:
            items.append(
                _error(
                    "missing_aux_join_key",
                    f"Auxiliary join key is missing: {table_requirement.table_name}.{join_key}",
                    requirements,
                    table_name=table_requirement.table_name,
                    field_name=join_key,
                    suggestion=f"Add join key column '{join_key}' to {table_requirement.table_name}.xlsx.",
                )
            )
            continue

        duplicated_values = _duplicated_matching_values(table.dataframe[join_key], main_key_values)
        if duplicated_values:
            items.append(
                _error(
                    "one_to_one_multiple_rows",
                    f"One-to-one table matches multiple rows: {table_requirement.table_name}.{join_key}",
                    requirements,
                    table_name=table_requirement.table_name,
                    field_name=join_key,
                    detail={"duplicated_values": duplicated_values},
                    suggestion="For one_to_one auxiliary tables, keep at most one row per main table key.",
                )
            )


def _validate_template_references(
    requirements: TemplateRequirements,
    tables: Mapping[str, LoadedTable],
    template_path: Path,
    items: list[ValidationItem],
) -> None:
    if not template_path.exists():
        return

    field_names_by_table = _field_names_by_table(requirements.fields)
    allowed_tables = {table.table_name for table in requirements.required_tables}

    references, _original_by_canonical, missing_variables = analyze_template_variables(template_path, requirements.fields)
    missing_original_paths = {missing.original_var_path for missing in missing_variables}
    for missing in missing_variables:
        items.append(
            _error(
                "missing_field",
                f"Template references unknown variable: {missing.original_var_path}",
                requirements,
                table_name=missing.table_name,
                field_name=missing.field_name,
                suggestion="Ensure the Chinese table/field name exists in entity_schema.xlsx.",
                detail={
                    "original_variable_path": missing.original_var_path,
                    "reason": missing.reason,
                },
            )
        )

    for reference in references:
        if (reference.original_variable_path or reference.variable_path) in missing_original_paths:
            continue
        table = tables.get(reference.table_name)
        schema_fields = field_names_by_table.get(reference.table_name)
        field_missing_in_schema = schema_fields is None or reference.field_name not in schema_fields
        field_missing_in_data = table is not None and reference.field_name not in table.columns

        if reference.table_name not in allowed_tables or field_missing_in_schema or field_missing_in_data:
            items.append(
                _error(
                    "missing_field",
                    f"Template references missing field: {reference.variable_path}",
                    requirements,
                    table_name=reference.table_name,
                    field_name=reference.field_name,
                    suggestion=f"Ensure {reference.variable_path} exists in schema and uploaded Excel data.",
                    detail={
                        "variable_path": reference.variable_path,
                        "original_variable_path": reference.original_variable_path or reference.variable_path,
                    },
                )
            )


def _build_report(task_id: str, items: list[ValidationItem]) -> ValidationReport:
    summary = ValidationSummary(
        error_count=sum(1 for item in items if item.level == ValidationLevel.ERROR),
        warning_count=sum(1 for item in items if item.level == ValidationLevel.WARNING),
        info_count=sum(1 for item in items if item.level == ValidationLevel.INFO),
    )
    if summary.error_count:
        status = ValidationStatus.FAILED
    elif summary.warning_count:
        status = ValidationStatus.PASSED_WITH_WARNINGS
    else:
        status = ValidationStatus.PASSED

    return ValidationReport(
        task_id=task_id,
        status=status,
        summary=summary,
        items=items,
        created_at=datetime.now(timezone.utc),
    )


def _coerce_loaded_tables(loaded_tables: Mapping[str, LoadedTable] | Any) -> Mapping[str, LoadedTable]:
    if isinstance(loaded_tables, Mapping):
        return loaded_tables
    tables = getattr(loaded_tables, "tables", None)
    if isinstance(tables, Mapping):
        return tables
    raise TypeError("loaded_tables must be a mapping or expose a tables mapping")


def _field_names_by_table(fields: list[FieldDefinition]) -> dict[str, set[str]]:
    fields_by_table: dict[str, set[str]] = {}
    for field in fields:
        fields_by_table.setdefault(field.table_name, set()).add(field.field_name)
    return fields_by_table


def _join_key_for(table_requirement: RequiredTable, requirements: TemplateRequirements) -> str:
    return table_requirement.table_join_key or table_requirement.main_join_key or requirements.primary_key_field


def _duplicated_non_empty_values(series: pd.Series) -> list[Any]:
    normalized = series[~series.map(_is_empty_cell)]
    duplicated = normalized[normalized.duplicated(keep=False)]
    return sorted({_json_safe_value(value) for value in duplicated.tolist()}, key=str)


def _duplicated_matching_values(series: pd.Series, allowed_values: set[Any]) -> list[Any]:
    normalized = series[~series.map(_is_empty_cell)]
    if allowed_values:
        normalized = normalized[normalized.map(_json_safe_value).isin(allowed_values)]
    duplicated = normalized[normalized.duplicated(keep=False)]
    return sorted({_json_safe_value(value) for value in duplicated.tolist()}, key=str)


def _non_empty_key_values(table: LoadedTable | None, key: str) -> set[Any]:
    if table is None or key not in table.columns:
        return set()
    return {
        _json_safe_value(value)
        for value in table.dataframe[key].tolist()
        if not _is_empty_cell(value)
    }


def _is_empty_cell(value: Any) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _json_safe_value(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value


def _excel_row_number(dataframe_index: Any) -> int:
    if isinstance(dataframe_index, int):
        return dataframe_index + 2
    return int(dataframe_index) + 2


def _error(
    code: str,
    message: str,
    requirements: TemplateRequirements,
    table_name: str | None = None,
    field_name: str | None = None,
    suggestion: str | None = None,
    detail: dict[str, Any] | None = None,
) -> ValidationItem:
    return _item(ValidationLevel.ERROR, code, message, requirements, table_name, field_name, suggestion, detail)


def _warning(
    code: str,
    message: str,
    requirements: TemplateRequirements,
    table_name: str | None = None,
    field_name: str | None = None,
    suggestion: str | None = None,
    detail: dict[str, Any] | None = None,
) -> ValidationItem:
    return _item(ValidationLevel.WARNING, code, message, requirements, table_name, field_name, suggestion, detail)


def _item(
    level: ValidationLevel,
    code: str,
    message: str,
    requirements: TemplateRequirements,
    table_name: str | None = None,
    field_name: str | None = None,
    suggestion: str | None = None,
    detail: dict[str, Any] | None = None,
) -> ValidationItem:
    return ValidationItem(
        level=level,
        code=code,
        message=message,
        table_name=table_name,
        field_name=field_name,
        template_id=requirements.template_id,
        template_file=requirements.template_file,
        suggestion=suggestion,
        detail=detail,
    )
