from __future__ import annotations

import sqlite3

from app.core.errors import AppError
from app.models.template_models import FieldDefinition, RequiredTable, TemplateRequirements


class TemplateRequirementService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get_template_requirements(self, template_id: int) -> TemplateRequirements:
        template = self._get_template(template_id)
        if template is None:
            raise AppError(
                code="TEMPLATE_NOT_FOUND",
                message=f"Template not found: {template_id}",
                status_code=404,
                details={"template_id": template_id},
            )

        required_tables = self._list_required_tables(template_id)
        if not required_tables:
            raise ValueError(f"template has no table requirements: {template_id}")

        primary_key_field = self._get_primary_key_field(template["main_table"])
        fields = self._list_fields_for_tables([table.table_name for table in required_tables])

        return TemplateRequirements(
            template_id=template["id"],
            template_name=template["template_name"],
            template_file=template["template_file"],
            template_path=template["template_path"],
            main_table=template["main_table"],
            primary_key_field=primary_key_field,
            required_tables=required_tables,
            fields=fields,
        )

    def _get_template(self, template_id: int) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()

    def _list_required_tables(self, template_id: int) -> list[RequiredTable]:
        rows = self.connection.execute(
            """
            SELECT table_name, table_name_cn, role, relation_type,
                   main_join_key, table_join_key, required
            FROM template_tables
            WHERE template_id = ?
            ORDER BY sort_order ASC, role DESC, table_name ASC
            """,
            (template_id,),
        ).fetchall()
        return [
            RequiredTable(
                table_name=row["table_name"],
                table_name_cn=row["table_name_cn"],
                role=row["role"],
                relation_type=row["relation_type"],
                main_join_key=row["main_join_key"],
                table_join_key=row["table_join_key"],
                required=bool(row["required"]),
            )
            for row in rows
        ]

    def _get_primary_key_field(self, table_name: str) -> str:
        rows = self.connection.execute(
            """
            SELECT field_name
            FROM fields
            WHERE table_name = ? AND is_primary_key = 1
            """,
            (table_name,),
        ).fetchall()
        if len(rows) != 1:
            raise ValueError(f"main table must have exactly one primary key: {table_name}")
        return rows[0]["field_name"]

    def _list_fields_for_tables(self, table_names: list[str]) -> list[FieldDefinition]:
        if not table_names:
            return []

        placeholders = ",".join("?" for _ in table_names)
        rows = self.connection.execute(
            f"""
            SELECT table_name, table_name_cn, field_name, field_name_cn, data_type,
                   is_primary_key, required, display_format, description,
                   created_at, updated_at
            FROM fields
            WHERE table_name IN ({placeholders})
            ORDER BY table_name ASC, id ASC
            """,
            tuple(table_names),
        ).fetchall()
        return [
            FieldDefinition(
                table_name=row["table_name"],
                table_name_cn=row["table_name_cn"],
                field_name=row["field_name"],
                field_name_cn=row["field_name_cn"],
                data_type=row["data_type"],
                is_primary_key=bool(row["is_primary_key"]),
                required=bool(row["required"]),
                display_format=row["display_format"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


def get_template_requirements(connection: sqlite3.Connection, template_id: int) -> TemplateRequirements:
    return TemplateRequirementService(connection).get_template_requirements(template_id)
