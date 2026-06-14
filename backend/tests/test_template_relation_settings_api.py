from io import BytesIO
from pathlib import Path
import sys

from openpyxl import load_workbook
import pandas as pd
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.connection import get_connection
from app.db.init_db import init_db

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


def seed_config(connection) -> None:
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
            ("loan_summary", "贷款汇总表", "branch_id", "支行编号", 0, NOW, NOW),
        ],
    )
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
    connection.execute(
        """
        INSERT INTO template_tables (
            template_id, table_name, table_name_cn, role, relation_type,
            main_join_key, table_join_key, required, sort_order, description, created_at, updated_at
        )
        VALUES (1, 'branch_main', '支行主表', 'main', 'main', '', '', 1, 0, '', ?, ?)
        """,
        (NOW, NOW),
    )


def relation_rows() -> list[dict]:
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
        },
        {
            "template_id": 1,
            "template_name": "普惠支行报告",
            "template_file": "template_1.docx",
            "table_name": "loan_summary",
            "table_name_cn": "贷款汇总表",
            "role": "aux",
            "relation_type": "one_to_one",
            "main_join_key": "branch_id",
            "table_join_key": "branch_id",
            "required": 1,
        },
    ]


def assert_success(payload: dict) -> None:
    assert payload["success"] is True
    assert payload["request_id"]
    assert payload["timestamp"]


def test_template_relation_list_filters_and_exports(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_config(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        list_response = client.get("/api/settings/template-relations", params={"template_id": 1})
        search_response = client.get("/api/settings/template-relations", params={"keyword": "支行"})
        export_response = client.get("/api/settings/template-relations/export")

    assert list_response.status_code == 200
    assert_success(list_response.json())
    assert list_response.json()["data"]["total"] == 1
    assert search_response.json()["data"]["total"] == 1
    workbook = load_workbook(BytesIO(export_response.content))
    assert workbook.active["A1"].value == "template_id"
    assert workbook.active["B1"].value == "template_name"


def test_template_relation_import_commit_updates_requirements(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_config(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        preview_response = client.post(
            "/api/settings/template-relations/import/preview",
            files={"file": ("template_relation.xlsx", excel_bytes(relation_rows()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        preview_payload = preview_response.json()
        commit_response = client.post(
            "/api/settings/template-relations/import/commit",
            json={"import_id": preview_payload["data"]["import_id"], "mode": "upsert"},
        )
        requirements_response = client.get("/api/templates/1/requirements")

    assert preview_response.status_code == 200
    assert preview_payload["data"]["can_commit"] is True
    assert commit_response.status_code == 200
    assert requirements_response.status_code == 200
    tables = requirements_response.json()["data"]["required_tables"]
    assert [table["table_name"] for table in tables] == ["branch_main", "loan_summary"]
