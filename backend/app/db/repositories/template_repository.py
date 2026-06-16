from __future__ import annotations

import sqlite3

from app.models.settings_models import TemplateFileRecord
from app.models.template_models import TemplateDetail, TemplateListItem, TemplateTableSummary


class TemplateRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.ensure_template_file_columns()

    def ensure_template_file_columns(self) -> None:
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(templates)").fetchall()
        }
        if "original_filename" not in columns:
            self.connection.execute("ALTER TABLE templates ADD COLUMN original_filename TEXT NOT NULL DEFAULT ''")
        if "description" not in columns:
            self.connection.execute("ALTER TABLE templates ADD COLUMN description TEXT NOT NULL DEFAULT ''")

    def list_templates(self, search: str | None = None, active_only: bool = True) -> list[TemplateListItem]:
        filters: list[str] = []
        params: list[object] = []

        if active_only:
            filters.append("t.is_active = 1")
        if search and search.strip():
            filters.append("LOWER(t.template_name) LIKE ?")
            params.append(f"%{search.strip().lower()}%")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self.connection.execute(
            f"""
            SELECT
                t.id,
                t.template_name,
                t.template_file,
                t.template_path,
                t.main_table,
                COALESCE(
                    NULLIF(MAX(CASE WHEN tt.role = 'main' THEN tt.table_name_cn ELSE '' END), ''),
                    NULLIF((
                        SELECT f.table_name_cn
                        FROM fields f
                        WHERE f.table_name = t.main_table AND f.table_name_cn <> ''
                        LIMIT 1
                    ), ''),
                    ''
                ) AS main_table_cn,
                SUM(CASE WHEN tt.role = 'aux' THEN 1 ELSE 0 END) AS aux_table_count,
                SUM(CASE WHEN tt.required = 1 THEN 1 ELSE 0 END) AS required_table_count,
                t.is_active,
                t.updated_at
            FROM templates t
            LEFT JOIN template_tables tt ON tt.template_id = t.id
            {where_clause}
            GROUP BY t.id
            ORDER BY t.updated_at DESC, t.id ASC
            """,
            tuple(params),
        ).fetchall()

        return [
            TemplateListItem(
                template_id=row["id"],
                template_name=row["template_name"],
                template_file=row["template_file"],
                template_path=row["template_path"],
                main_table=row["main_table"],
                main_table_cn=row["main_table_cn"] or "",
                aux_table_count=int(row["aux_table_count"] or 0),
                required_table_count=int(row["required_table_count"] or 0),
                is_active=bool(row["is_active"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_template_detail(self, template_id: int) -> TemplateDetail | None:
        template = self.connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table, is_active, updated_at
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()
        if template is None:
            return None

        table_rows = self.connection.execute(
            """
            SELECT table_name, table_name_cn, role, relation_type, required,
                   main_join_key, table_join_key
            FROM template_tables
            WHERE template_id = ?
            ORDER BY sort_order ASC, role DESC, table_name ASC
            """,
            (template_id,),
        ).fetchall()
        tables = [self._table_summary(row) for row in table_rows]
        main_table = next((table for table in tables if table.role == "main"), None)
        if main_table is None:
            main_table = TemplateTableSummary(
                table_name=template["main_table"],
                table_name_cn=self._lookup_table_name_cn(template["main_table"]),
                role="main",
                relation_type="main",
                required=True,
            )
        aux_tables = [table for table in tables if table.role != "main"]

        return TemplateDetail(
            template_id=template["id"],
            template_name=template["template_name"],
            template_file=template["template_file"],
            template_path=template["template_path"],
            main_table=main_table,
            aux_tables=aux_tables,
            is_active=bool(template["is_active"]),
            updated_at=template["updated_at"],
        )

    def _lookup_table_name_cn(self, table_name: str) -> str:
        row = self.connection.execute(
            """
            SELECT table_name_cn
            FROM fields
            WHERE table_name = ? AND table_name_cn <> ''
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()
        return row["table_name_cn"] if row else ""

    def _table_summary(self, row: sqlite3.Row) -> TemplateTableSummary:
        return TemplateTableSummary(
            table_name=row["table_name"],
            table_name_cn=row["table_name_cn"],
            role=row["role"],
            relation_type=row["relation_type"],
            required=bool(row["required"]),
            main_join_key=row["main_join_key"],
            table_join_key=row["table_join_key"],
        )

    def list_template_files(self) -> list[TemplateFileRecord]:
        rows = self.connection.execute(
            """
            SELECT id, template_name, template_file, original_filename, template_path,
                   description, is_active, created_at, updated_at
            FROM templates
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        return [self._template_file_record(row) for row in rows]

    def get_template_file(self, template_id: int) -> TemplateFileRecord | None:
        row = self.connection.execute(
            """
            SELECT id, template_name, template_file, original_filename, template_path,
                   description, is_active, created_at, updated_at
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()
        return self._template_file_record(row) if row else None

    def get_template_row(self, template_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table,
                   output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()

    def get_template_by_name_file(self, template_name: str, template_file: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table,
                   output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
            FROM templates
            WHERE template_name = ? AND template_file = ?
            """,
            (template_name, template_file),
        ).fetchone()

    def template_file_exists(self, template_file: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM templates WHERE template_file = ? LIMIT 1",
            (template_file,),
        ).fetchone()
        return row is not None

    def create_template_relation_template(
        self,
        template_name: str,
        template_file: str,
        main_table: str,
        now: str,
        template_id: int | None = None,
    ) -> int:
        columns = [
            "template_name",
            "template_file",
            "template_path",
            "original_filename",
            "description",
            "main_table",
            "output_name_pattern",
            "ai_enabled_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        values: list[object] = [
            template_name,
            template_file,
            f"templates/{template_file}",
            template_file,
            "",
            main_table,
            "{template_name}_{primary_key_value}.docx",
            1,
            1,
            now,
            now,
        ]
        if template_id is not None:
            columns.insert(0, "id")
            values.insert(0, template_id)
        placeholders = ", ".join("?" for _ in columns)
        cursor = self.connection.execute(
            f"INSERT INTO templates ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )
        return int(template_id or cursor.lastrowid)

    def update_template_relation_metadata(
        self,
        template_id: int,
        template_name: str,
        template_file: str,
        main_table: str,
        now: str,
    ) -> None:
        self.connection.execute(
            """
            UPDATE templates
            SET template_name = ?, template_file = ?, template_path = ?,
                original_filename = CASE WHEN original_filename = '' THEN ? ELSE original_filename END,
                main_table = ?, is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (
                template_name,
                template_file,
                f"templates/{template_file}",
                template_file,
                main_table,
                now,
                template_id,
            ),
        )

    def create_template_file_placeholder(
        self,
        template_name: str,
        original_filename: str,
        description: str,
        now: str,
        placeholder_file: str,
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT INTO templates (
                template_name, template_file, template_path, original_filename,
                description, main_table, output_name_pattern, ai_enabled_default,
                is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, '', '{template_name}_{primary_key_value}.docx', 1, 1, ?, ?)
            """,
            (
                template_name,
                placeholder_file,
                f"templates/{placeholder_file}",
                original_filename,
                description,
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

    def update_template_file_path(self, template_id: int, template_file: str, template_path: str, now: str) -> None:
        self.connection.execute(
            """
            UPDATE templates
            SET template_file = ?, template_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (template_file, template_path, now, template_id),
        )

    def update_template_original_filename(self, template_id: int, original_filename: str, now: str) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE templates
            SET original_filename = ?, updated_at = ?
            WHERE id = ?
            """,
            (original_filename, now, template_id),
        )
        return cursor.rowcount > 0

    def activate_template(self, template_id: int, now: str) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE templates
            SET is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (now, template_id),
        )
        return cursor.rowcount > 0

    def deactivate_template(self, template_id: int, now: str) -> bool:
        cursor = self.connection.execute(
            """
            UPDATE templates
            SET is_active = 0, updated_at = ?
            WHERE id = ?
            """,
            (now, template_id),
        )
        return cursor.rowcount > 0

    def delete_template_metadata(self, template_id: int) -> None:
        self.connection.execute("DELETE FROM templates WHERE id = ?", (template_id,))

    def _template_file_record(self, row: sqlite3.Row) -> TemplateFileRecord:
        return TemplateFileRecord(
            template_id=row["id"],
            template_name=row["template_name"],
            template_file=row["template_file"],
            original_filename=row["original_filename"] or row["template_file"],
            template_path=row["template_path"],
            description=row["description"] or "",
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
