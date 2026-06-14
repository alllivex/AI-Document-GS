from io import BytesIO
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.connection import get_connection
from app.db.init_db import init_db
from app.db.repositories.field_repository import FieldRepository
from app.services.entity_schema_service import EntitySchemaService

NOW = "2026-06-14T12:00:00+00:00"


def reset_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'config' / 'db.sqlite').as_posix()}")
    get_settings.cache_clear()
    return get_settings()


def excel_bytes(rows: list[dict]) -> bytes:
    buffer = BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def seed_field(connection) -> None:
    connection.execute(
        """
        INSERT INTO fields (
            table_name, table_name_cn, field_name, field_name_cn, data_type,
            is_primary_key, required, display_format, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("branch_main", "支行主表", "branch_id", "支行编号", "string", 1, 1, "", "", NOW, NOW),
    )


def test_entity_schema_preview_does_not_write_and_commit_upserts(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    file_bytes = excel_bytes(
        [
            {
                "table_name": "branch_main",
                "table_name_cn": "支行主表",
                "field_name": "branch_id",
                "field_name_cn": "支行编号",
                "data_type": "string",
                "is_primary_key": 1,
                "required": "是",
                "display_format": "",
                "description": "updated",
            },
            {
                "table_name": "branch_main",
                "table_name_cn": "支行主表",
                "field_name": "branch_name",
                "field_name_cn": "支行名称",
                "data_type": "string",
                "is_primary_key": 0,
                "required": "true",
                "display_format": "",
                "description": "",
            },
        ]
    )

    with get_connection(settings.database_path) as connection:
        seed_field(connection)
        service = EntitySchemaService(FieldRepository(connection), settings)
        preview = service.preview_import("entity_schema.xlsx", file_bytes)
        rows_after_preview = connection.execute("SELECT COUNT(*) AS total FROM fields").fetchone()["total"]
        service.commit_import(preview.import_id, "upsert")
        rows_after_commit = connection.execute("SELECT COUNT(*) AS total FROM fields").fetchone()["total"]
        updated = connection.execute(
            "SELECT description FROM fields WHERE table_name = 'branch_main' AND field_name = 'branch_id'"
        ).fetchone()["description"]

    assert preview.can_commit is True
    assert preview.summary.total_rows == 2
    assert preview.summary.update_count == 1
    assert preview.summary.create_count == 1
    assert rows_after_preview == 1
    assert rows_after_commit == 2
    assert updated == "updated"


def test_entity_schema_preview_blocks_invalid_rows(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    file_bytes = excel_bytes(
        [
            {
                "table_name": "branch_main",
                "table_name_cn": "支行主表",
                "field_name": "branch_id",
                "field_name_cn": "支行编号",
                "data_type": "string",
                "is_primary_key": 1,
                "required": 1,
            },
            {
                "table_name": "branch_main",
                "table_name_cn": "支行主表",
                "field_name": "branch_code",
                "field_name_cn": "支行编号",
                "data_type": "bad_type",
                "is_primary_key": "maybe",
                "required": 0,
            },
        ]
    )

    with get_connection(settings.database_path) as connection:
        service = EntitySchemaService(FieldRepository(connection), settings)
        preview = service.preview_import("entity_schema.xlsx", file_bytes)

    assert preview.can_commit is False
    assert preview.summary.error_count >= 2
    messages = [item.message for item in preview.items if item.level == "error"]
    assert any("data_type" in message for message in messages)
    assert any("boolean" in message for message in messages)


def test_entity_schema_preview_requires_required_columns(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    file_bytes = excel_bytes([{"table_name": "branch_main", "field_name": "branch_id"}])

    with get_connection(settings.database_path) as connection:
        service = EntitySchemaService(FieldRepository(connection), settings)
        preview = service.preview_import("entity_schema.xlsx", file_bytes)

    assert preview.can_commit is False
    assert preview.summary.error_count == 1
    assert "缺少必需列" in preview.items[0].message
