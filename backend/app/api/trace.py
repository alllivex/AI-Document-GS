from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.response import success_response
from app.db.connection import get_connection

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
        for item in trace_file.get("trace_items", []):
            if item.get("trace_id") == trace_id:
                return success_response(item)

    raise AppError("TRACE_NOT_FOUND", f"Trace not found: {trace_id}", 404, {"trace_id": trace_id})


def _resolve_project_path(path_value: str, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path
