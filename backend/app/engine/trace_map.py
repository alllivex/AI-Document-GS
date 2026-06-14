from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.engine.data_loader import LoadedTable
from app.engine.value_formatter import normalize_raw_value
from app.models.enums import DataType, RelationType
from app.models.template_models import FieldDefinition
from app.models.trace_models import TraceItem


TraceMap = dict[str, list[TraceItem]]


def build_trace_item(
    *,
    doc_id: str,
    var_path: str,
    table: LoadedTable,
    field_name: str,
    raw_value: Any,
    display_value: str,
    pk_field: str,
    pk_value: str,
    row_index: int,
    source_relation_type: RelationType | str,
    occurrence_index: int = 0,
    field_schema: FieldDefinition | None = None,
) -> TraceItem:
    trace_id = _make_trace_id(doc_id, var_path, occurrence_index)
    return TraceItem(
        trace_id=trace_id,
        var_path=var_path,
        table_name=table.table_name,
        table_name_cn=_field_table_name_cn(field_schema),
        field_name=field_name,
        field_name_cn=_field_name_cn(field_schema),
        source_file=table.source_file,
        source_file_path=table.source_file_path,
        pk_field=pk_field,
        pk_value=pk_value,
        row_index=row_index,
        excel_row_number=row_index + 2,
        column_index=table.column_index_map.get(field_name),
        excel_column_letter=table.excel_column_letter_map.get(field_name),
        raw_value=normalize_raw_value(raw_value),
        display_value=display_value,
        value_type=_field_data_type(field_schema),
        display_format=_field_display_format(field_schema),
        occurrence_index=occurrence_index,
        source_relation_type=source_relation_type,
        created_at=datetime.now(timezone.utc),
    )


def add_trace_item(trace_map: TraceMap, trace_item: TraceItem) -> None:
    trace_map.setdefault(trace_item.var_path, []).append(trace_item)


def _make_trace_id(doc_id: str, var_path: str, occurrence_index: int) -> str:
    return f"trace_{uuid5(NAMESPACE_URL, f'{doc_id}:{var_path}:{occurrence_index}')}"


def _field_table_name_cn(field_schema: FieldDefinition | None) -> str:
    if field_schema is None:
        return ""
    return field_schema.table_name_cn


def _field_name_cn(field_schema: FieldDefinition | None) -> str:
    if field_schema is None:
        return ""
    return field_schema.field_name_cn


def _field_data_type(field_schema: FieldDefinition | None) -> DataType:
    if field_schema is None:
        return DataType.STRING
    return DataType(field_schema.data_type)


def _field_display_format(field_schema: FieldDefinition | None) -> str:
    if field_schema is None:
        return ""
    return field_schema.display_format
