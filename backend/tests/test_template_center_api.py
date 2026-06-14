from pathlib import Path
import sys

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


def seed_templates(connection) -> None:
    connection.executemany(
        """
        INSERT INTO templates (
            id, template_name, template_file, template_path, main_table,
            output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        [
            (1, "普惠支行报告", "branch.docx", "templates/branch.docx", "branch_main", "{template_name}_{primary_key_value}.docx", 1, NOW, NOW),
            (2, "停用模板", "inactive.docx", "templates/inactive.docx", "inactive_main", "{template_name}_{primary_key_value}.docx", 0, NOW, NOW),
        ],
    )
    connection.executemany(
        """
        INSERT INTO template_tables (
            template_id, table_name, table_name_cn, role, relation_type,
            main_join_key, table_join_key, required, sort_order, description,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
        """,
        [
            (1, "branch_main", "支行主表", "main", "main", "", "", 1, 0, NOW, NOW),
            (1, "loan_summary", "贷款汇总表", "aux", "one_to_one", "branch_id", "branch_id", 1, 1, NOW, NOW),
            (1, "risk_items", "风险事项表", "aux", "one_to_many", "branch_id", "branch_id", 0, 2, NOW, NOW),
            (2, "inactive_main", "停用主表", "main", "main", "", "", 1, 0, NOW, NOW),
        ],
    )


def assert_success(payload: dict) -> None:
    assert payload["success"] is True
    assert payload["request_id"]
    assert payload["timestamp"]


def test_template_center_list_supports_summary_search_and_active_filter(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_templates(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/templates", params={"search": "支行"})

    payload = response.json()
    assert response.status_code == 200
    assert_success(payload)
    assert payload["data"]["total"] == 1
    item = payload["data"]["items"][0]
    assert item["template_id"] == 1
    assert item["main_table_cn"] == "支行主表"
    assert item["aux_table_count"] == 2
    assert item["required_table_count"] == 2
    assert item["is_active"] is True


def test_template_center_list_can_include_inactive_templates(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_templates(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/templates", params={"active_only": "false"})

    payload = response.json()
    assert response.status_code == 200
    assert_success(payload)
    assert payload["data"]["total"] == 2


def test_template_center_detail_returns_main_and_aux_tables(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        seed_templates(connection)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/templates/1")

    payload = response.json()
    assert response.status_code == 200
    assert_success(payload)
    detail = payload["data"]
    assert detail["template_name"] == "普惠支行报告"
    assert detail["template_file"] == "branch.docx"
    assert detail["main_table"]["table_name"] == "branch_main"
    assert detail["main_table"]["relation_type"] == "main"
    assert [table["table_name"] for table in detail["aux_tables"]] == ["loan_summary", "risk_items"]
    assert detail["aux_tables"][0]["relation_type"] == "one_to_one"
    assert detail["aux_tables"][1]["required"] is False
