from pathlib import Path
import json
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.connection import get_connection
from app.db.init_db import init_db
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.uploaded_file_repository import UploadedFileRepository
from app.services.task_service import TaskService

NOW = "2026-06-14T13:00:00+00:00"


def reset_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'config' / 'db.sqlite').as_posix()}")
    get_settings.cache_clear()
    return get_settings()


def seed_template_config(connection) -> None:
    connection.execute(
        """
        INSERT INTO templates (
            id, template_name, template_file, template_path, main_table,
            output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "客户尽调报告",
            "due_diligence.docx",
            "templates/due_diligence.docx",
            "customer_info",
            "{template_name}_{primary_key_value}.docx",
            1,
            1,
            NOW,
            NOW,
        ),
    )
    connection.executemany(
        """
        INSERT INTO template_tables (
            template_id, table_name, table_name_cn, role, relation_type,
            main_join_key, table_join_key, required, sort_order, description,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "customer_info", "客户信息表", "main", "main", "", "", 1, 0, "", NOW, NOW),
            (1, "loan_summary", "贷款汇总表", "aux", "one_to_one", "customer_id", "customer_id", 1, 1, "", NOW, NOW),
        ],
    )
    connection.executemany(
        """
        INSERT INTO fields (
            table_name, table_name_cn, field_name, field_name_cn, data_type,
            is_primary_key, required, display_format, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("customer_info", "客户信息表", "customer_id", "客户编号", "string", 1, 1, "", "", NOW, NOW),
            ("customer_info", "客户信息表", "customer_name", "客户名称", "string", 0, 1, "", "", NOW, NOW),
            ("loan_summary", "贷款汇总表", "customer_id", "客户编号", "string", 1, 1, "", "", NOW, NOW),
        ],
    )


def prepare_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    connection_context = get_connection(settings.database_path)
    connection = connection_context.__enter__()
    seed_template_config(connection)
    return settings, connection_context, connection, TaskService(connection, settings)


def test_create_task_creates_record_workspace_and_meta_json(tmp_path, monkeypatch) -> None:
    settings, context, connection, service = prepare_service(tmp_path, monkeypatch)
    try:
        result = service.create_task("客户尽调报告批量生成", template_id=1, ai_enabled=True)
        task = TaskRepository(connection).get(result.task_id)
    finally:
        context.__exit__(None, None, None)

    task_dir = settings.tasks_dir / result.task_id
    meta_path = task_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    assert task is not None
    assert task.status == "created"
    assert task_dir.is_dir()
    assert (task_dir / "data").is_dir()
    assert (task_dir / "output").is_dir()
    assert (task_dir / "validation").is_dir()
    assert (task_dir / "logs").is_dir()
    assert meta["task_id"] == result.task_id
    assert meta["template_id"] == 1
    assert meta["primary_key_field"] == "customer_id"
    assert meta["paths"]["task_dir"] == f"tasks/{result.task_id}"


def test_upload_task_file_saves_xlsx_and_records_uploaded_file(tmp_path, monkeypatch) -> None:
    settings, context, connection, service = prepare_service(tmp_path, monkeypatch)
    try:
        task = service.create_task("客户尽调报告批量生成", template_id=1)
        response = service.upload_task_file(
            task_id=task.task_id,
            table_name="customer_info",
            file_bytes=b"first content",
            original_filename="客户信息表.xlsx",
        )
        uploaded_files = UploadedFileRepository(connection).list_by_task(task.task_id)
        updated_task = TaskRepository(connection).get(task.task_id)
    finally:
        context.__exit__(None, None, None)

    file_path = settings.tasks_dir / task.task_id / "data" / "customer_info.xlsx"
    assert response.file_path == f"tasks/{task.task_id}/data/customer_info.xlsx"
    assert file_path.read_bytes() == b"first content"
    assert len(uploaded_files) == 1
    assert uploaded_files[0].original_filename == "客户信息表.xlsx"
    assert updated_task is not None
    assert updated_task.status == "uploaded"


def test_upload_non_xlsx_raises_upload_file_invalid(tmp_path, monkeypatch) -> None:
    settings, context, connection, service = prepare_service(tmp_path, monkeypatch)
    try:
        task = service.create_task("客户尽调报告批量生成", template_id=1)
        with pytest.raises(AppError) as exc_info:
            service.upload_task_file(
                task_id=task.task_id,
                table_name="customer_info",
                file_bytes=b"not xlsx",
                original_filename="customer_info.csv",
            )
    finally:
        context.__exit__(None, None, None)

    assert exc_info.value.code == "UPLOAD_FILE_INVALID"


def test_repeated_upload_overwrites_file_and_updates_uploaded_file_record(tmp_path, monkeypatch) -> None:
    settings, context, connection, service = prepare_service(tmp_path, monkeypatch)
    try:
        task = service.create_task("客户尽调报告批量生成", template_id=1)
        service.upload_task_file(task.task_id, "customer_info", b"first", "first.xlsx")
        service.upload_task_file(task.task_id, "customer_info", b"second", "second.xlsx")
        uploaded_files = UploadedFileRepository(connection).list_by_task(task.task_id)
    finally:
        context.__exit__(None, None, None)

    file_path = settings.tasks_dir / task.task_id / "data" / "customer_info.xlsx"
    meta = json.loads((settings.tasks_dir / task.task_id / "meta.json").read_text(encoding="utf-8"))

    assert file_path.read_bytes() == b"second"
    assert len(uploaded_files) == 1
    assert uploaded_files[0].original_filename == "second.xlsx"
    assert meta["uploaded_files"][0]["original_filename"] == "second.xlsx"
