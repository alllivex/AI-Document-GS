from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.response import success_response
from app.db.connection import get_connection
from app.db.repositories.document_repository import DocumentRepository

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{doc_id}/preview")
async def get_document_preview(doc_id: str):
    settings = get_settings()
    with get_connection() as connection:
        document = DocumentRepository(connection).get(doc_id)
        if document is None:
            raise AppError("DOCUMENT_NOT_FOUND", f"Document not found: {doc_id}", 404, {"doc_id": doc_id})

    preview_path = _resolve_project_path(document.preview_path, settings.project_root)
    if not preview_path.exists():
        raise AppError("FILE_NOT_FOUND", f"Preview file not found: {doc_id}", 404, {"doc_id": doc_id})
    return success_response(json.loads(preview_path.read_text(encoding="utf-8")))


@router.get("/{doc_id}/download")
async def download_document(doc_id: str):
    settings = get_settings()
    with get_connection() as connection:
        document = DocumentRepository(connection).get(doc_id)
        if document is None:
            raise AppError("DOCUMENT_NOT_FOUND", f"Document not found: {doc_id}", 404, {"doc_id": doc_id})

    output_path = _resolve_project_path(document.output_path, settings.project_root)
    if not output_path.exists() or not output_path.is_file():
        raise AppError("FILE_NOT_FOUND", f"Document file not found: {doc_id}", 404, {"doc_id": doc_id})
    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=document.output_filename,
    )


def _resolve_project_path(path_value: str, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path
