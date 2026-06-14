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


def seed_fields(connection) -> None:
    connection.executemany(
        """
        INSERT INTO fields (
            table_name, table_name_cn, field_name, field_name_cn, data_type,
            is_primary_key, required, display_format, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("branch_main", "支行主表", "branch_id", "支行编号", "string", 1, 1, "", "", NOW, NOW),
            ("branch_main", "支行主表", "branch_name", "支行名称", "string", 0, 1, "", "", NOW, NOW),
            ("loan_summary", "贷款汇总表", "loan_balance", "贷款余额", "amount", 0, 0, "amount_2", "", NOW, NOW),
        ],
    )


def assert_success(payload: dict) -> None:
    assert payload["success"] is True
    assert payload["request_id"]
    assert payload["timestamp"]


def test_entity_schema_list_filters_and_searches(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_fields(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        table_response = client.get("/api/settings/entity-schema", params={"table_name": "branch_main"})
        keyword_response = client.get("/api/settings/entity-schema", params={"keyword": "贷款"})

    table_payload = table_response.json()
    keyword_payload = keyword_response.json()
    assert table_response.status_code == 200
    assert_success(table_payload)
    assert table_payload["data"]["total"] == 2
    assert table_payload["data"]["items"][0]["is_active"] is True
    assert keyword_response.status_code == 200
    assert keyword_payload["data"]["total"] == 1
    assert keyword_payload["data"]["items"][0]["field_name"] == "loan_balance"


def test_entity_schema_import_preview_commit_and_export(tmp_path, monkeypatch) -> None:
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
                "display_format": "",
                "description": "",
            }
        ]
    )

    from app.main import create_app

    with TestClient(create_app()) as client:
        preview_response = client.post(
            "/api/settings/entity-schema/import/preview",
            files={"file": ("entity_schema.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        preview_payload = preview_response.json()
        import_id = preview_payload["data"]["import_id"]
        commit_response = client.post(
            "/api/settings/entity-schema/import/commit",
            json={"import_id": import_id, "mode": "upsert"},
        )
        list_response = client.get("/api/settings/entity-schema")
        export_response = client.get("/api/settings/entity-schema/export")

    assert preview_response.status_code == 200
    assert_success(preview_payload)
    assert preview_payload["data"]["can_commit"] is True
    assert preview_payload["data"]["summary"]["create_count"] == 1
    assert commit_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1
    assert export_response.status_code == 200
    workbook = load_workbook(BytesIO(export_response.content))
    assert workbook.active["A1"].value == "table_name"
    assert workbook.active["A2"].value == "branch_main"


def test_entity_schema_commit_rejects_preview_with_errors(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    file_bytes = excel_bytes(
        [
            {
                "table_name": "branch_main",
                "table_name_cn": "支行主表",
                "field_name": "branch_id",
                "field_name_cn": "支行编号",
                "data_type": "bad",
            }
        ]
    )

    from app.main import create_app

    with TestClient(create_app()) as client:
        preview_response = client.post(
            "/api/settings/entity-schema/import/preview",
            files={"file": ("entity_schema.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        import_id = preview_response.json()["data"]["import_id"]
        commit_response = client.post(
            "/api/settings/entity-schema/import/commit",
            json={"import_id": import_id, "mode": "upsert"},
        )

    assert preview_response.status_code == 200
    assert preview_response.json()["data"]["can_commit"] is False
    assert commit_response.status_code == 400
    assert commit_response.json()["error"]["code"] == "VALIDATION_FAILED"
