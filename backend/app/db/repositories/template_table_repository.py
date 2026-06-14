from __future__ import annotations

import sqlite3

from app.models.settings_models import TemplateRelationRecord


class TemplateTableRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_relations(
        self,
        template_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TemplateRelationRecord], int]:
        filters: list[str] = []
        params: list[object] = []
        if template_id:
            filters.append("tt.template_id = ?")
            params.append(template_id)
        if keyword and keyword.strip():
            like_value = f"%{keyword.strip().lower()}%"
            filters.append(
                """
                (
                    LOWER(t.template_name) LIKE ?
                    OR LOWER(t.template_file) LIKE ?
                    OR LOWER(tt.table_name) LIKE ?
                    OR LOWER(tt.table_name_cn) LIKE ?
                    OR LOWER(tt.description) LIKE ?
                )
                """
            )
            params.extend([like_value, like_value, like_value, like_value, like_value])

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        total = self.connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM template_tables tt
            JOIN templates t ON t.id = tt.template_id
            {where_clause}
            """,
            tuple(params),
        ).fetchone()["total"]

        limit = max(page_size, 1)
        offset = max(page - 1, 0) * limit
        rows = self.connection.execute(
            f"""
            SELECT tt.id, tt.template_id, t.template_name, t.template_file,
                   tt.table_name, tt.table_name_cn, tt.role, tt.relation_type,
                   tt.main_join_key, tt.table_join_key, tt.required, tt.description
            FROM template_tables tt
            JOIN templates t ON t.id = tt.template_id
            {where_clause}
            ORDER BY t.id ASC, tt.sort_order ASC, tt.role DESC, tt.table_name ASC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()
        return [self._record(row) for row in rows], int(total)

    def existing_keys(self) -> set[tuple[int, str]]:
        rows = self.connection.execute("SELECT template_id, table_name FROM template_tables").fetchall()
        return {(int(row["template_id"]), row["table_name"]) for row in rows}

    def export_relations(self) -> list[TemplateRelationRecord]:
        rows = self.connection.execute(
            """
            SELECT tt.id, tt.template_id, t.template_name, t.template_file,
                   tt.table_name, tt.table_name_cn, tt.role, tt.relation_type,
                   tt.main_join_key, tt.table_join_key, tt.required, tt.description
            FROM template_tables tt
            JOIN templates t ON t.id = tt.template_id
            ORDER BY t.id ASC, tt.sort_order ASC, tt.role DESC, tt.table_name ASC
            """
        ).fetchall()
        return [self._record(row) for row in rows]

    def upsert_relation(
        self,
        template_id: int,
        table_name: str,
        table_name_cn: str,
        role: str,
        relation_type: str,
        main_join_key: str,
        table_join_key: str,
        required: bool,
        sort_order: int,
        description: str,
        now: str,
    ) -> None:
        existing = self.connection.execute(
            """
            SELECT id
            FROM template_tables
            WHERE template_id = ? AND table_name = ?
            """,
            (template_id, table_name),
        ).fetchone()
        if existing:
            self.connection.execute(
                """
                UPDATE template_tables
                SET table_name_cn = ?, role = ?, relation_type = ?,
                    main_join_key = ?, table_join_key = ?, required = ?,
                    sort_order = ?, description = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    table_name_cn,
                    role,
                    relation_type,
                    main_join_key,
                    table_join_key,
                    int(required),
                    sort_order,
                    description,
                    now,
                    existing["id"],
                ),
            )
        else:
            self.connection.execute(
                """
                INSERT INTO template_tables (
                    template_id, table_name, table_name_cn, role, relation_type,
                    main_join_key, table_join_key, required, sort_order,
                    description, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    template_id,
                    table_name,
                    table_name_cn,
                    role,
                    relation_type,
                    main_join_key,
                    table_join_key,
                    int(required),
                    sort_order,
                    description,
                    now,
                    now,
                ),
            )

    def _record(self, row: sqlite3.Row) -> TemplateRelationRecord:
        return TemplateRelationRecord(
            id=row["id"],
            template_id=row["template_id"],
            template_name=row["template_name"],
            template_file=row["template_file"],
            table_name=row["table_name"],
            table_name_cn=row["table_name_cn"],
            role=row["role"],
            relation_type=row["relation_type"],
            main_join_key=row["main_join_key"],
            table_join_key=row["table_join_key"],
            required=bool(row["required"]),
            description=row["description"],
        )
