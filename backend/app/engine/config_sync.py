from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.db.connection import get_connection
from app.db.init_db import init_db
from app.engine.schema_loader import load_entity_schema
from app.engine.template_relation_loader import (
    TemplateRelationDefinition,
    get_template_configs,
    load_template_relation,
)
from app.models.template_models import FieldDefinition


def sync_config_to_db(
    schema_xlsx: Path,
    relation_xlsx: Path,
    database_path: Path | None = None,
) -> None:
    fields = load_entity_schema(schema_xlsx)
    relations = load_template_relation(relation_xlsx)

    if database_path is not None:
        init_db(database_path)

    with get_connection(database_path) as connection:
        sync_fields(connection, fields)
        sync_templates(connection, relations)
        sync_template_tables(connection, relations)


def sync_fields(connection: sqlite3.Connection, fields: list[FieldDefinition]) -> None:
    now = _now_iso()
    for field in fields:
        connection.execute(
            """
            INSERT INTO fields (
                table_name, table_name_cn, field_name, field_name_cn, data_type,
                is_primary_key, required, display_format, description, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(table_name, field_name) DO UPDATE SET
                table_name_cn = excluded.table_name_cn,
                field_name_cn = excluded.field_name_cn,
                data_type = excluded.data_type,
                is_primary_key = excluded.is_primary_key,
                required = excluded.required,
                display_format = excluded.display_format,
                description = excluded.description,
                updated_at = excluded.updated_at
            """,
            (
                field.table_name,
                field.table_name_cn,
                field.field_name,
                field.field_name_cn,
                field.data_type,
                1 if field.is_primary_key else 0,
                1 if field.required else 0,
                field.display_format,
                field.description,
                now,
                now,
            ),
        )


def sync_templates(connection: sqlite3.Connection, relations: list[TemplateRelationDefinition]) -> None:
    now = _now_iso()
    for template in get_template_configs(relations):
        connection.execute(
            """
            INSERT INTO templates (
                id, template_name, template_file, template_path, main_table,
                output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                template_name = excluded.template_name,
                template_file = excluded.template_file,
                template_path = excluded.template_path,
                main_table = excluded.main_table,
                output_name_pattern = excluded.output_name_pattern,
                ai_enabled_default = excluded.ai_enabled_default,
                is_active = excluded.is_active,
                updated_at = excluded.updated_at
            """,
            (
                template.template_id,
                template.template_name,
                template.template_file,
                f"templates/{template.template_file}",
                template.main_table,
                "{template_name}_{primary_key_value}.docx",
                1,
                1,
                now,
                now,
            ),
        )


def sync_template_tables(connection: sqlite3.Connection, relations: list[TemplateRelationDefinition]) -> None:
    now = _now_iso()
    for relation in relations:
        connection.execute(
            """
            INSERT INTO template_tables (
                template_id, table_name, table_name_cn, role, relation_type,
                main_join_key, table_join_key, required, sort_order, description,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(template_id, table_name) DO UPDATE SET
                table_name_cn = excluded.table_name_cn,
                role = excluded.role,
                relation_type = excluded.relation_type,
                main_join_key = excluded.main_join_key,
                table_join_key = excluded.table_join_key,
                required = excluded.required,
                sort_order = excluded.sort_order,
                description = excluded.description,
                updated_at = excluded.updated_at
            """,
            (
                relation.template_id,
                relation.table_name,
                relation.table_name_cn,
                relation.role,
                relation.relation_type,
                relation.main_join_key,
                relation.table_join_key,
                1 if relation.required else 0,
                relation.sort_order,
                relation.description,
                now,
                now,
            ),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
