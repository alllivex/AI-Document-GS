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
from app.db.repositories.template_repository import TemplateRepository
from app.db.repositories.template_table_repository import TemplateTableRepository
from app.services.template_relation_service import TemplateRelationService

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


def seed_fields(connection) -> None:
    connection.executemany(
        """
        INSERT INTO fields (
            table_name, table_name_cn, field_name, field_name_cn, data_type,
            is_primary_key, required, display_format, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 'string', ?, 1, '', '', ?, ?)
        """,
        [
            ("branch_main", "支行主表", "branch_id", "支行编号", 1, NOW, NOW),
            ("branch_main", "支行主表", "branch_name", "支行名称", 0, NOW, NOW),
            ("loan_summary", "贷款汇总表", "branch_id", "支行编号", 0, NOW, NOW),
            ("loan_summary", "贷款汇总表", "loan_balance", "贷款余额", 0, NOW, NOW),
        ],
    )


def seed_template(connection) -> None:
    connection.execute(
        """
        INSERT INTO templates (
            id, template_name, template_file, template_path, main_table,
            output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
        )
        VALUES (1, '普惠支行报告', 'template_1.docx', 'templates/template_1.docx', 'branch_main',
                '{template_name}_{primary_key_value}.docx', 1, 1, ?, ?)
        """,
        (NOW, NOW),
    )


def service(connection, settings) -> TemplateRelationService:
    return TemplateRelationService(
        TemplateRepository(connection),
        TemplateTableRepository(connection),
        FieldRepository(connection),
        settings,
    )


def valid_rows() -> list[dict]:
    return [
        {
            "template_id": 1,
            "template_name": "普惠支行报告",
            "template_file": "template_1.docx",
            "table_name": "branch_main",
            "table_name_cn": "支行主表",
            "role": "main",
            "relation_type": "main",
            "main_join_key": "",
            "table_join_key": "",
            "required": 1,
            "sort_order": 0,
            "description": "",
        },
        {
            "template_id": 1,
            "template_name": "普惠支行报告",
            "template_file": "template_1.docx",
            "table_name": "loan_summary",
            "table_name_cn": "贷款汇总表",
            "role": "aux",
            "relation_type": "one_to_many",
            "main_join_key": "branch_id",
            "table_join_key": "branch_id",
            "required": 1,
            "sort_order": 1,
            "description": "",
        },
    ]


def test_template_relation_preview_does_not_write_and_commit_upserts(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_fields(connection)
        seed_template(connection)
        current_service = service(connection, settings)
        preview = current_service.preview_import("template_relation.xlsx", excel_bytes(valid_rows()))
        before_commit = connection.execute("SELECT COUNT(*) AS total FROM template_tables").fetchone()["total"]
        current_service.commit_import(preview.import_id, "upsert")
        after_commit = connection.execute("SELECT COUNT(*) AS total FROM template_tables").fetchone()["total"]
        template = connection.execute("SELECT main_table FROM templates WHERE id = 1").fetchone()

    assert preview.can_commit is True
    assert preview.summary.create_count == 2
    assert before_commit == 0
    assert after_commit == 2
    assert template["main_table"] == "branch_main"


def test_template_relation_preview_rejects_multiple_main_tables(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    rows = valid_rows()
    rows[1]["role"] = "main"
    rows[1]["relation_type"] = "main"
    with get_connection(settings.database_path) as connection:
        seed_fields(connection)
        seed_template(connection)
        preview = service(connection, settings).preview_import("template_relation.xlsx", excel_bytes(rows))

    assert preview.can_commit is False
    assert any("必须且只能有一个主表" in item.message for item in preview.items)


def test_template_relation_preview_rejects_aux_missing_join_keys(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    rows = valid_rows()
    rows[1]["main_join_key"] = ""
    rows[1]["table_join_key"] = ""
    with get_connection(settings.database_path) as connection:
        seed_fields(connection)
        seed_template(connection)
        preview = service(connection, settings).preview_import("template_relation.xlsx", excel_bytes(rows))

    assert preview.can_commit is False
    messages = [item.message for item in preview.items]
    assert any("main_join_key 必填" in message for message in messages)
    assert any("table_join_key 必填" in message for message in messages)


def test_template_relation_preview_rejects_missing_relation_fields(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    rows = valid_rows()
    rows[1]["main_join_key"] = "missing_main_key"
    rows[1]["table_join_key"] = "missing_table_key"
    with get_connection(settings.database_path) as connection:
        seed_fields(connection)
        seed_template(connection)
        preview = service(connection, settings).preview_import("template_relation.xlsx", excel_bytes(rows))

    assert preview.can_commit is False
    messages = [item.message for item in preview.items]
    assert any("main_join_key 不存在" in message for message in messages)
    assert any("table_join_key 不存在" in message for message in messages)
