from __future__ import annotations

import sqlite3

from app.models.settings_models import EntitySchemaFieldRecord, EntitySchemaTableSummary
from app.models.template_models import FieldDefinition


class FieldRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_fields(
        self,
        table_name: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[EntitySchemaFieldRecord], int]:
        filters: list[str] = []
        params: list[object] = []

        if table_name and table_name.strip():
            filters.append("table_name = ?")
            params.append(table_name.strip())
        if keyword and keyword.strip():
            like_value = f"%{keyword.strip().lower()}%"
            filters.append(
                """
                (
                    LOWER(table_name) LIKE ?
                    OR LOWER(table_name_cn) LIKE ?
                    OR LOWER(field_name) LIKE ?
                    OR LOWER(field_name_cn) LIKE ?
                    OR LOWER(description) LIKE ?
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value, like_value])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        total = self.connection.execute(
            f"SELECT COUNT(*) AS total FROM fields {where_clause}",
            tuple(params),
        ).fetchone()["total"]

        limit = max(page_size, 1)
        offset = max(page - 1, 0) * limit
        rows = self.connection.execute(
            f"""
            SELECT id, table_name, table_name_cn, field_name, field_name_cn,
                   data_type, is_primary_key, required, display_format, description
            FROM fields
            {where_clause}
            ORDER BY table_name ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
        return [self._record(row) for row in rows], int(total)

    def list_table_summaries(self, keyword: str | None = None) -> list[EntitySchemaTableSummary]:
        filters: list[str] = []
        params: list[object] = []
        if keyword and keyword.strip():
            like_value = f"%{keyword.strip().lower()}%"
            filters.append(
                """
                (
                    LOWER(table_name) LIKE ?
                    OR LOWER(table_name_cn) LIKE ?
                    OR LOWER(field_name) LIKE ?
                    OR LOWER(field_name_cn) LIKE ?
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self.connection.execute(
            f"""
            SELECT table_name, table_name_cn, field_name, is_primary_key, required
            FROM fields
            {where_clause}
            ORDER BY table_name ASC, id ASC
            """,
            tuple(params),
        ).fetchall()

        summaries: dict[str, EntitySchemaTableSummary] = {}
        for row in rows:
            table_name = row["table_name"]
            summary = summaries.get(table_name)
            if summary is None:
                summary = EntitySchemaTableSummary(
                    table_name=table_name,
                    table_name_cn=row["table_name_cn"],
                )
                summaries[table_name] = summary
            summary.field_count += 1
            if row["is_primary_key"]:
                summary.primary_key_fields.append(row["field_name"])
            if row["required"]:
                summary.required_field_count += 1
        return list(summaries.values())

    def get_existing_keys(self) -> set[tuple[str, str]]:
        rows = self.connection.execute("SELECT table_name, field_name FROM fields").fetchall()
        return {(row["table_name"], row["field_name"]) for row in rows}

    def table_names(self) -> set[str]:
        rows = self.connection.execute("SELECT DISTINCT table_name FROM fields").fetchall()
        return {row["table_name"] for row in rows}

    def field_names_by_table(self) -> dict[str, set[str]]:
        rows = self.connection.execute("SELECT table_name, field_name FROM fields").fetchall()
        result: dict[str, set[str]] = {}
        for row in rows:
            result.setdefault(row["table_name"], set()).add(row["field_name"])
        return result

    def export_fields(self) -> list[EntitySchemaFieldRecord]:
        rows = self.connection.execute(
            """
            SELECT id, table_name, table_name_cn, field_name, field_name_cn,
                   data_type, is_primary_key, required, display_format, description
            FROM fields
            ORDER BY table_name ASC, id ASC
            """
        ).fetchall()
        return [self._record(row) for row in rows]

    def upsert_fields(self, fields: list[FieldDefinition], now: str) -> None:
        for field in fields:
            existing = self.connection.execute(
                """
                SELECT id
                FROM fields
                WHERE table_name = ? AND field_name = ?
                """,
                (field.table_name, field.field_name),
            ).fetchone()
            if existing:
                self.connection.execute(
                    """
                    UPDATE fields
                    SET table_name_cn = ?, field_name_cn = ?, data_type = ?,
                        is_primary_key = ?, required = ?, display_format = ?,
                        description = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        field.table_name_cn,
                        field.field_name_cn,
                        self._data_type_value(field),
                        int(field.is_primary_key),
                        int(field.required),
                        field.display_format,
                        field.description,
                        now,
                        existing["id"],
                    ),
                )
            else:
                self.connection.execute(
                    """
                    INSERT INTO fields (
                        table_name, table_name_cn, field_name, field_name_cn,
                        data_type, is_primary_key, required, display_format,
                        description, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        field.table_name,
                        field.table_name_cn,
                        field.field_name,
                        field.field_name_cn,
                        self._data_type_value(field),
                        int(field.is_primary_key),
                        int(field.required),
                        field.display_format,
                        field.description,
                        now,
                        now,
                    ),
                )

    def _record(self, row: sqlite3.Row) -> EntitySchemaFieldRecord:
        return EntitySchemaFieldRecord(
            id=row["id"],
            table_name=row["table_name"],
            table_name_cn=row["table_name_cn"],
            field_name=row["field_name"],
            field_name_cn=row["field_name_cn"],
            data_type=row["data_type"],
            is_primary_key=bool(row["is_primary_key"]),
            required=bool(row["required"]),
            display_format=row["display_format"],
            description=row["description"],
            is_active=True,
        )

    def _data_type_value(self, field: FieldDefinition) -> str:
        return field.data_type.value if hasattr(field.data_type, "value") else str(field.data_type)
