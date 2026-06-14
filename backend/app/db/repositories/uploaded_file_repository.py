from __future__ import annotations

import sqlite3
from datetime import datetime

from app.models.file_models import UploadedFileRecord


class UploadedFileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert(self, uploaded_file: UploadedFileRecord) -> UploadedFileRecord:
        params = self._to_db_params(uploaded_file)
        self.connection.execute(
            """
            INSERT INTO uploaded_files (
                task_id, table_name, original_filename, stored_filename, file_path,
                file_size, file_ext, row_count, column_count, checksum, uploaded_at
            )
            VALUES (
                :task_id, :table_name, :original_filename, :stored_filename, :file_path,
                :file_size, :file_ext, :row_count, :column_count, :checksum, :uploaded_at
            )
            ON CONFLICT(task_id, table_name) DO UPDATE SET
                original_filename = excluded.original_filename,
                stored_filename = excluded.stored_filename,
                file_path = excluded.file_path,
                file_size = excluded.file_size,
                file_ext = excluded.file_ext,
                row_count = excluded.row_count,
                column_count = excluded.column_count,
                checksum = excluded.checksum,
                uploaded_at = excluded.uploaded_at
            """,
            params,
        )
        saved = self.get_by_task_and_table(uploaded_file.task_id, uploaded_file.table_name)
        if saved is None:
            raise RuntimeError(f"failed to upsert uploaded file: {uploaded_file.task_id}/{uploaded_file.table_name}")
        return saved

    def get_by_task_and_table(self, task_id: str, table_name: str) -> UploadedFileRecord | None:
        row = self.connection.execute(
            """
            SELECT task_id, table_name, original_filename, stored_filename, file_path,
                   file_path AS path, file_size, file_ext, row_count, column_count,
                   checksum, uploaded_at
            FROM uploaded_files
            WHERE task_id = ? AND table_name = ?
            """,
            (task_id, table_name),
        ).fetchone()
        return UploadedFileRecord(**dict(row)) if row else None

    def list_by_task(self, task_id: str) -> list[UploadedFileRecord]:
        rows = self.connection.execute(
            """
            SELECT task_id, table_name, original_filename, stored_filename, file_path,
                   file_path AS path, file_size, file_ext, row_count, column_count,
                   checksum, uploaded_at
            FROM uploaded_files
            WHERE task_id = ?
            ORDER BY table_name ASC
            """,
            (task_id,),
        ).fetchall()
        return [UploadedFileRecord(**dict(row)) for row in rows]

    @staticmethod
    def _to_db_params(uploaded_file: UploadedFileRecord) -> dict[str, object]:
        data = uploaded_file.model_dump(mode="python")
        if not data.get("file_path"):
            data["file_path"] = data["path"]
        value = data["uploaded_at"]
        data["uploaded_at"] = value.isoformat() if isinstance(value, datetime) else value
        return data
