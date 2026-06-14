from __future__ import annotations

import sqlite3
from datetime import datetime

from app.models.task_models import DocumentRecord


class DocumentRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, document: DocumentRecord) -> DocumentRecord:
        self.connection.execute(
            """
            INSERT INTO documents (
                doc_id, task_id, template_id, template_name, primary_key_value,
                output_filename, output_path, trace_filename, trace_path,
                preview_filename, preview_path, status, ai_status, trace_count,
                ai_block_count, error_message, created_at, updated_at
            )
            VALUES (
                :doc_id, :task_id, :template_id, :template_name, :primary_key_value,
                :output_filename, :output_path, :trace_filename, :trace_path,
                :preview_filename, :preview_path, :status, :ai_status, :trace_count,
                :ai_block_count, :error_message, :created_at, :updated_at
            )
            """,
            self._to_db_params(document),
        )
        created = self.get(document.doc_id)
        if created is None:
            raise RuntimeError(f"failed to create document: {document.doc_id}")
        return created

    def get(self, doc_id: str) -> DocumentRecord | None:
        row = self.connection.execute(
            """
            SELECT doc_id, task_id, template_id, template_name, primary_key_value,
                   output_filename, output_path, trace_filename, trace_path,
                   preview_filename, preview_path, status, ai_status, trace_count,
                   ai_block_count, error_message, created_at, updated_at
            FROM documents
            WHERE doc_id = ?
            """,
            (doc_id,),
        ).fetchone()
        return DocumentRecord(**dict(row)) if row else None

    def list_by_task(self, task_id: str) -> list[DocumentRecord]:
        rows = self.connection.execute(
            """
            SELECT doc_id, task_id, template_id, template_name, primary_key_value,
                   output_filename, output_path, trace_filename, trace_path,
                   preview_filename, preview_path, status, ai_status, trace_count,
                   ai_block_count, error_message, created_at, updated_at
            FROM documents
            WHERE task_id = ?
            ORDER BY primary_key_value ASC
            """,
            (task_id,),
        ).fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]

    @staticmethod
    def _to_db_params(document: DocumentRecord) -> dict[str, object]:
        data = document.model_dump(mode="python")
        data["status"] = str(data["status"])
        data["ai_status"] = str(data["ai_status"])
        for key in ("created_at", "updated_at"):
            value = data[key]
            data[key] = value.isoformat() if isinstance(value, datetime) else value
        return data
