from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.engine.data_loader import LoadedTable
from app.engine.trace_map import TraceMap, add_trace_item, build_trace_item
from app.engine.value_formatter import format_display_value, normalize_raw_value
from app.models.enums import RelationType, TableRole
from app.models.template_models import FieldDefinition, RequiredTable, TemplateRequirements


class BuildContextsInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str
    template_requirements: TemplateRequirements
    loaded_tables: Any


class ReportContextBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    doc_id: str
    primary_key_value: str
    context: dict[str, Any]
    trace_map: TraceMap
    source_rows: dict[str, Any]


ReportContextList = list[ReportContextBundle]


def build_report_contexts(
    requirements: TemplateRequirements,
    loaded_tables: Mapping[str, LoadedTable] | Any,
    task_id: str = "",
) -> ReportContextList:
    tables = _coerce_loaded_tables(loaded_tables)
    main_req = _find_main_table_requirement(requirements)
    main_table = _get_loaded_table(tables, main_req.table_name)
    pk_field = requirements.primary_key_field

    if pk_field not in main_table.columns:
        raise ValueError(f"main table '{main_table.table_name}' missing primary key field: {pk_field}")

    field_schemas = _build_field_schema_map(requirements.fields)
    bundles: ReportContextList = []

    for row_position, (row_index, main_row) in enumerate(main_table.dataframe.iterrows()):
        pk_value = str(main_row[pk_field])
        doc_id = _make_doc_id(task_id, requirements.template_id, pk_value)
        context: dict[str, Any] = {}
        trace_map: TraceMap = {}
        source_rows: dict[str, Any] = {}

        context[main_req.table_name] = _build_row_context(
            doc_id=doc_id,
            table=main_table,
            row=main_row,
            row_index=_to_row_index(row_index, row_position),
            pk_field=pk_field,
            pk_value=pk_value,
            relation_type=RelationType.MAIN,
            occurrence_index=0,
            field_schemas=field_schemas,
            trace_map=trace_map,
        )
        source_rows[main_req.table_name] = _normalize_row(main_row)

        for aux_req in _iter_aux_table_requirements(requirements, main_req.table_name):
            aux_table = _get_loaded_table(tables, aux_req.table_name)
            matched_rows = _match_aux_rows(main_row, aux_table.dataframe, aux_req, pk_field)

            if _relation_value(aux_req.relation_type) == RelationType.ONE_TO_ONE.value:
                context[aux_req.table_name], source_rows[aux_req.table_name] = _build_one_to_one_context(
                    doc_id=doc_id,
                    table=aux_table,
                    matched_rows=matched_rows,
                    pk_field=pk_field,
                    pk_value=pk_value,
                    field_schemas=field_schemas,
                    trace_map=trace_map,
                )
            elif _relation_value(aux_req.relation_type) == RelationType.ONE_TO_MANY.value:
                context[aux_req.table_name], source_rows[aux_req.table_name] = _build_one_to_many_context(
                    doc_id=doc_id,
                    table=aux_table,
                    matched_rows=matched_rows,
                    pk_field=pk_field,
                    pk_value=pk_value,
                    field_schemas=field_schemas,
                    trace_map=trace_map,
                )
            else:
                raise ValueError(
                    f"unsupported auxiliary relation type for table '{aux_req.table_name}': "
                    f"{aux_req.relation_type}"
                )

        bundles.append(
            ReportContextBundle(
                doc_id=doc_id,
                primary_key_value=pk_value,
                context=context,
                trace_map=trace_map,
                source_rows=source_rows,
            )
        )

    return bundles


def build_contexts(input_data: BuildContextsInput) -> ReportContextList:
    return build_report_contexts(
        requirements=input_data.template_requirements,
        loaded_tables=input_data.loaded_tables,
        task_id=input_data.task_id,
    )


def _build_row_context(
    *,
    doc_id: str,
    table: LoadedTable,
    row: pd.Series,
    row_index: int,
    pk_field: str,
    pk_value: str,
    relation_type: RelationType,
    occurrence_index: int,
    field_schemas: dict[tuple[str, str], FieldDefinition],
    trace_map: TraceMap,
) -> dict[str, str]:
    row_context: dict[str, str] = {}
    for field_name in table.columns:
        field_schema = field_schemas.get((table.table_name, field_name))
        raw_value = row[field_name]
        display_value = format_display_value(raw_value, field_schema)
        row_context[field_name] = display_value

        var_path = f"{table.table_name}.{field_name}"
        add_trace_item(
            trace_map,
            build_trace_item(
                doc_id=doc_id,
                var_path=var_path,
                table=table,
                field_name=field_name,
                raw_value=raw_value,
                display_value=display_value,
                pk_field=pk_field,
                pk_value=pk_value,
                row_index=row_index,
                source_relation_type=relation_type,
                occurrence_index=occurrence_index,
                field_schema=field_schema,
            ),
        )
    return row_context


def _build_one_to_one_context(
    *,
    doc_id: str,
    table: LoadedTable,
    matched_rows: pd.DataFrame,
    pk_field: str,
    pk_value: str,
    field_schemas: dict[tuple[str, str], FieldDefinition],
    trace_map: TraceMap,
) -> tuple[dict[str, str], dict[str, Any]]:
    if matched_rows.empty:
        return {}, {}

    row_index, row = next(matched_rows.iterrows())
    row_context = _build_row_context(
        doc_id=doc_id,
        table=table,
        row=row,
        row_index=_to_row_index(row_index, 0),
        pk_field=pk_field,
        pk_value=pk_value,
        relation_type=RelationType.ONE_TO_ONE,
        occurrence_index=0,
        field_schemas=field_schemas,
        trace_map=trace_map,
    )
    return row_context, _normalize_row(row)


def _build_one_to_many_context(
    *,
    doc_id: str,
    table: LoadedTable,
    matched_rows: pd.DataFrame,
    pk_field: str,
    pk_value: str,
    field_schemas: dict[tuple[str, str], FieldDefinition],
    trace_map: TraceMap,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    contexts: list[dict[str, str]] = []
    source_rows: list[dict[str, Any]] = []

    for occurrence_index, (row_index, row) in enumerate(matched_rows.iterrows()):
        contexts.append(
            _build_row_context(
                doc_id=doc_id,
                table=table,
                row=row,
                row_index=_to_row_index(row_index, occurrence_index),
                pk_field=pk_field,
                pk_value=pk_value,
                relation_type=RelationType.ONE_TO_MANY,
                occurrence_index=occurrence_index,
                field_schemas=field_schemas,
                trace_map=trace_map,
            )
        )
        source_rows.append(_normalize_row(row))

    return contexts, source_rows


def _match_aux_rows(
    main_row: pd.Series,
    aux_dataframe: pd.DataFrame,
    aux_req: RequiredTable,
    pk_field: str,
) -> pd.DataFrame:
    main_join_key = aux_req.main_join_key or pk_field
    table_join_key = aux_req.table_join_key or main_join_key

    if main_join_key not in main_row.index:
        raise ValueError(f"main table missing join key '{main_join_key}' for aux table '{aux_req.table_name}'")
    if table_join_key not in aux_dataframe.columns:
        raise ValueError(f"aux table '{aux_req.table_name}' missing join key: {table_join_key}")

    join_value = str(main_row[main_join_key])
    return aux_dataframe[aux_dataframe[table_join_key].astype(str) == join_value]


def _find_main_table_requirement(requirements: TemplateRequirements) -> RequiredTable:
    for table_req in requirements.required_tables:
        if _role_value(table_req.role) == TableRole.MAIN.value:
            return table_req
    for table_req in requirements.required_tables:
        if table_req.table_name == requirements.main_table:
            return table_req
    raise ValueError(f"template requirements missing main table: {requirements.main_table}")


def _iter_aux_table_requirements(
    requirements: TemplateRequirements,
    main_table_name: str,
) -> list[RequiredTable]:
    return [
        table_req
        for table_req in requirements.required_tables
        if table_req.table_name != main_table_name and _role_value(table_req.role) != TableRole.MAIN.value
    ]


def _build_field_schema_map(fields: list[FieldDefinition]) -> dict[tuple[str, str], FieldDefinition]:
    return {(field.table_name, field.field_name): field for field in fields}


def _coerce_loaded_tables(loaded_tables: Mapping[str, LoadedTable] | Any) -> Mapping[str, LoadedTable]:
    if isinstance(loaded_tables, Mapping):
        return loaded_tables
    tables = getattr(loaded_tables, "tables", None)
    if isinstance(tables, Mapping):
        return tables
    raise TypeError("loaded_tables must be a mapping or an object with a 'tables' mapping")


def _get_loaded_table(tables: Mapping[str, LoadedTable], table_name: str) -> LoadedTable:
    try:
        return tables[table_name]
    except KeyError as exc:
        raise ValueError(f"loaded table not found: {table_name}") from exc


def _normalize_row(row: pd.Series) -> dict[str, Any]:
    return {field_name: normalize_raw_value(value) for field_name, value in row.to_dict().items()}


def _to_row_index(row_index: Any, fallback: int) -> int:
    try:
        return int(row_index)
    except (TypeError, ValueError):
        return fallback


def _make_doc_id(task_id: str, template_id: int, pk_value: str) -> str:
    namespace = f"{task_id}:{template_id}:{pk_value}"
    return f"doc_{uuid5(NAMESPACE_URL, namespace)}"


def _role_value(role: TableRole | str) -> str:
    return getattr(role, "value", role)


def _relation_value(relation_type: RelationType | str) -> str:
    return getattr(relation_type, "value", relation_type)
