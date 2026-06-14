from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.connection import get_connection
from app.db.init_db import init_db
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.uploaded_file_repository import UploadedFileRepository
from app.models.enums import AIStatus, DocumentStatus, TaskStatus
from app.models.file_models import UploadedFileRecord
from app.models.task_models import DocumentRecord, TaskRecord

NOW = datetime(2026, 6, 14, 10, 30, tzinfo=timezone.utc)


def insert_template(connection) -> None:
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
            NOW.isoformat(),
            NOW.isoformat(),
        ),
    )


def make_task() -> TaskRecord:
    return TaskRecord(
        task_id="task_20260614_103000_a1b2c3",
        task_name="客户尽调报告批量生成",
        template_id=1,
        template_name="客户尽调报告",
        status=TaskStatus.CREATED,
        ai_enabled=True,
        main_table="customer_info",
        primary_key_field="customer_id",
        total_rows=0,
        success_count=0,
        failed_count=0,
        warning_count=0,
        error_count=0,
        task_dir="tasks/task_20260614_103000_a1b2c3",
        validation_report_path="",
        error_message="",
        created_by="system",
        created_at=NOW,
        updated_at=NOW,
    )


def make_document() -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc_550e8400-e29b-41d4-a716-446655440000",
        task_id="task_20260614_103000_a1b2c3",
        template_id=1,
        template_name="客户尽调报告",
        primary_key_value="C001",
        output_filename="客户尽调报告_C001.docx",
        output_path="tasks/task_20260614_103000_a1b2c3/output/客户尽调报告_C001.docx",
        trace_filename="客户尽调报告_C001.trace.json",
        trace_path="tasks/task_20260614_103000_a1b2c3/output/客户尽调报告_C001.trace.json",
        preview_filename="客户尽调报告_C001.preview.json",
        preview_path="tasks/task_20260614_103000_a1b2c3/output/客户尽调报告_C001.preview.json",
        status=DocumentStatus.SUCCESS,
        ai_status=AIStatus.SUCCESS,
        trace_count=12,
        ai_block_count=1,
        error_message="",
        created_at=NOW,
        updated_at=NOW,
    )


def make_uploaded_file(original_filename: str, row_count: int) -> UploadedFileRecord:
    return UploadedFileRecord(
        task_id="task_20260614_103000_a1b2c3",
        table_name="customer_info",
        original_filename=original_filename,
        stored_filename="customer_info.xlsx",
        path="tasks/task_20260614_103000_a1b2c3/data/customer_info.xlsx",
        file_path="tasks/task_20260614_103000_a1b2c3/data/customer_info.xlsx",
        file_size=20480,
        file_ext=".xlsx",
        row_count=row_count,
        column_count=8,
        checksum="",
        uploaded_at=NOW,
    )


def test_task_repository_create_get_update_status_and_list(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"
    init_db(database_path)

    with get_connection(database_path) as connection:
        insert_template(connection)
        repository = TaskRepository(connection)

        created = repository.create(make_task())
        fetched = repository.get(created.task_id)
        updated = repository.update_status(created.task_id, TaskStatus.UPLOADED)
        items = repository.list()
        uploaded_items = repository.list(status=TaskStatus.UPLOADED)

    assert fetched is not None
    assert fetched.task_name == "客户尽调报告批量生成"
    assert updated is not None
    assert updated.status == "uploaded"
    assert len(items) == 1
    assert len(uploaded_items) == 1
    assert uploaded_items[0].task_id == "task_20260614_103000_a1b2c3"


def test_document_and_uploaded_file_repositories(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"
    init_db(database_path)

    with get_connection(database_path) as connection:
        insert_template(connection)
        task_repository = TaskRepository(connection)
        task_repository.create(make_task())

        document_repository = DocumentRepository(connection)
        created_document = document_repository.create(make_document())
        fetched_document = document_repository.get(created_document.doc_id)
        documents = document_repository.list_by_task("task_20260614_103000_a1b2c3")

        uploaded_file_repository = UploadedFileRepository(connection)
        uploaded_file_repository.upsert(make_uploaded_file("客户信息表.xlsx", 3))
        uploaded_file_repository.upsert(make_uploaded_file("客户信息表-新版.xlsx", 4))
        uploaded_files = uploaded_file_repository.list_by_task("task_20260614_103000_a1b2c3")

    assert fetched_document is not None
    assert fetched_document.status == "success"
    assert len(documents) == 1
    assert documents[0].primary_key_value == "C001"
    assert len(uploaded_files) == 1
    assert uploaded_files[0].original_filename == "客户信息表-新版.xlsx"
    assert uploaded_files[0].row_count == 4
