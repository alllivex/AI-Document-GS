from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.response import success_response
from app.db.connection import get_connection
from app.engine.trace_builder import build_source_record_view
from app.models.trace_models import FieldTraceDetail, TraceItem

router = APIRouter(prefix="/api/trace", tags=["trace"])


@router.get("/{trace_id}")
async def get_trace_item(trace_id: str):
    settings = get_settings()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT trace_path
            FROM documents
            WHERE trace_path != ''
            ORDER BY created_at ASC
            """
        ).fetchall()

    for row in rows:
        trace_path = _resolve_project_path(row["trace_path"], settings.project_root)
        if not trace_path.exists():
            continue
        trace_file = json.loads(trace_path.read_text(encoding="utf-8"))
        for item in trace_file.get("ai_traces", []):
            if item.get("trace_id") == trace_id:
                return success_response(item)
        for item in trace_file.get("condition_traces", []):
            if item.get("trace_id") == trace_id:
                return success_response(item)
        for item in trace_file.get("loop_traces", []):
            if item.get("trace_id") == trace_id:
                return success_response(item)

        trace_items = [TraceItem.model_validate(item) for item in trace_file.get("trace_items", [])]
        for item in trace_file.get("trace_items", []):
            if item.get("trace_id") == trace_id:
                trace_item = TraceItem.model_validate(item)
                detail = FieldTraceDetail(
                    trace_id=trace_item.trace_id,
                    task_id=trace_file.get("task_id", ""),
                    doc_id=trace_file.get("doc_id", ""),
                    primary_key_value=trace_file.get("primary_key_value", trace_item.pk_value),
                    var_path=trace_item.var_path,
                    table_name=trace_item.table_name,
                    table_name_cn=trace_item.table_name_cn,
                    field_name=trace_item.field_name,
                    field_name_cn=trace_item.field_name_cn,
                    source_record=build_source_record_view(
                        trace_items,
                        trace_item,
                        highlighted_fields={trace_item.field_name},
                        highlight_reason="clicked",
                    ),
                )
                return success_response(detail.model_dump(mode="json"))

    raise AppError("TRACE_NOT_FOUND", f"Trace not found: {trace_id}", 404, {"trace_id": trace_id})


def _resolve_project_path(path_value: str, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path
