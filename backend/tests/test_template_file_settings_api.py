from io import BytesIO
from pathlib import Path
import sqlite3
import sys

from docx import Document
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.connection import get_connection
from app.db.init_db import init_db


def reset_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'config' / 'db.sqlite').as_posix()}")
    get_settings.cache_clear()
    return get_settings()


def docx_bytes() -> bytes:
    buffer = BytesIO()
    document = Document()
    document.add_paragraph("Hello {{ customer_info.customer_name }}")
    document.save(buffer)
    return buffer.getvalue()


def assert_success(payload: dict) -> None:
    assert payload["success"] is True
    assert payload["request_id"]
    assert payload["timestamp"]


def test_template_file_upload_list_download_and_deactivate(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        upload_response = client.post(
            "/api/settings/template-files",
            data={"template_name": "普惠支行报告", "description": "模板说明"},
            files={
                "file": (
                    "普惠支行报告.docx",
                    docx_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert_success(upload_payload)
        record = upload_payload["data"]
        template_id = record["template_id"]
        assert record["template_file"] == f"template_{template_id}.docx"
        assert record["template_path"] == f"templates/template_{template_id}.docx"
        assert record["original_filename"] == "普惠支行报告.docx"
        assert record["description"] == "模板说明"
        assert (settings.templates_dir / f"template_{template_id}.docx").is_file()

        list_response = client.get("/api/settings/template-files")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert_success(list_payload)
        assert list_payload["data"]["total"] == 1
        assert list_payload["data"]["items"][0]["template_name"] == "普惠支行报告"

        center_response = client.get("/api/templates")
        assert center_response.status_code == 200
        assert center_response.json()["data"]["total"] == 1

        download_response = client.get(f"/api/settings/template-files/{template_id}/download")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert download_response.content.startswith(b"PK")

        deactivate_response = client.delete(f"/api/settings/template-files/{template_id}")
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["data"]["is_active"] is False
        assert (settings.templates_dir / f"template_{template_id}.docx").is_file()

        active_center_response = client.get("/api/templates")
        assert active_center_response.status_code == 200
        assert active_center_response.json()["data"]["total"] == 0

    with sqlite3.connect(settings.database_path) as connection:
        row = connection.execute(
            """
            SELECT template_name, template_file, original_filename, description, is_active
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()
    assert row == ("普惠支行报告", f"template_{template_id}.docx", "普惠支行报告.docx", "模板说明", 0)


def test_template_file_upload_rejects_non_docx(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/settings/template-files",
            data={"template_name": "错误模板", "description": ""},
            files={"file": ("bad.txt", b"not docx", "text/plain")},
        )

    payload = response.json()
    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"]["code"] == "UPLOAD_FILE_INVALID"


def test_template_file_upload_rejects_invalid_docx_content(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/settings/template-files",
            data={"template_name": "损坏模板", "description": ""},
            files={
                "file": (
                    "broken.docx",
                    b"not a valid docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    payload = response.json()
    assert response.status_code == 400
    assert payload["success"] is False
    assert payload["error"]["code"] == "UPLOAD_FILE_INVALID"
    assert "有效的 .docx" in payload["error"]["message"]


def test_template_file_api_adds_metadata_columns_for_existing_schema(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/settings/template-files")

    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total": 0}
    with get_connection(settings.database_path) as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(templates)").fetchall()}
    assert "original_filename" in columns
    assert "description" in columns
