from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.models.enums import TaskStatus
from app.models.task_models import TaskRecord


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_task(row: sqlite3.Row | None) -> TaskRecord | None:
    if row is None:
        return None
    return TaskRecord(**dict(row))


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, task: TaskRecord) -> TaskRecord:
        self.connection.execute(
            """
            INSERT INTO tasks (
                task_id, task_name, template_id, template_name, status, ai_enabled,
                main_table, primary_key_field, total_rows, success_count, failed_count,
                warning_count, error_count, task_dir, validation_report_path,
                error_message, created_by, created_at, updated_at, started_at, completed_at
            )
            VALUES (
                :task_id, :task_name, :template_id, :template_name, :status, :ai_enabled,
                :main_table, :primary_key_field, :total_rows, :success_count, :failed_count,
                :warning_count, :error_count, :task_dir, :validation_report_path,
                :error_message, :created_by, :created_at, :updated_at, :started_at, :completed_at
            )
            """,
            self._to_db_params(task),
        )
        created = self.get(task.task_id)
        if created is None:
            raise RuntimeError(f"failed to create task: {task.task_id}")
        return created

    def get(self, task_id: str) -> TaskRecord | None:
        row = self.connection.execute(
            """
            SELECT task_id, task_name, template_id, template_name, status, ai_enabled,
                   main_table, primary_key_field, total_rows, success_count, failed_count,
                   warning_count, error_count, task_dir, validation_report_path,
                   error_message, created_by, created_at, updated_at, started_at, completed_at
            FROM tasks
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
        return _row_to_task(row)

    def update_status(
        self,
        task_id: str,
        status: TaskStatus | str,
        error_message: str | None = None,
        updated_at: datetime | None = None,
    ) -> TaskRecord | None:
        status_value = status.value if isinstance(status, TaskStatus) else status
        current_time = updated_at or _utc_now()
        if error_message is None:
            self.connection.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (status_value, current_time.isoformat(), task_id),
            )
        else:
            self.connection.execute(
                """
                UPDATE tasks
                SET status = ?, error_message = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (status_value, error_message, current_time.isoformat(), task_id),
            )
        return self.get(task_id)

    def list(
        self,
        status: TaskStatus | str | None = None,
        keyword: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TaskRecord]:
        where_sql, params = self._build_list_filter(status, keyword)
        rows = self.connection.execute(
            f"""
            SELECT task_id, task_name, template_id, template_name, status, ai_enabled,
                   main_table, primary_key_field, total_rows, success_count, failed_count,
                   warning_count, error_count, task_dir, validation_report_path,
                   error_message, created_by, created_at, updated_at, started_at, completed_at
            FROM tasks
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (*params, limit, offset),
        ).fetchall()
        return [TaskRecord(**dict(row)) for row in rows]

    def count(self, status: TaskStatus | str | None = None, keyword: str | None = None) -> int:
        where_sql, params = self._build_list_filter(status, keyword)
        row = self.connection.execute(
            f"SELECT COUNT(*) AS total FROM tasks {where_sql}",
            params,
        ).fetchone()
        return int(row["total"])

    @staticmethod
    def _build_list_filter(
        status: TaskStatus | str | None,
        keyword: str | None,
    ) -> tuple[str, tuple[object, ...]]:
        conditions: list[str] = []
        params: list[object] = []
        if status is not None:
            status_value = status.value if isinstance(status, TaskStatus) else status
            conditions.append("status = ?")
            params.append(status_value)
        if keyword:
            search = f"%{keyword.strip()}%"
            conditions.append(
                "(task_name LIKE ? OR template_name LIKE ? OR main_table LIKE ? OR task_id LIKE ?)"
            )
            params.extend([search] * 4)
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return where_sql, tuple(params)

    @staticmethod
    def _to_db_params(task: TaskRecord) -> dict[str, object]:
        data = task.model_dump(mode="python")
        data["status"] = str(data["status"])
        data["ai_enabled"] = 1 if data["ai_enabled"] else 0
        for key in ("created_at", "updated_at", "started_at", "completed_at"):
            value = data[key]
            data[key] = value.isoformat() if isinstance(value, datetime) else value
        return data
