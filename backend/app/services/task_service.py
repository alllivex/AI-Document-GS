from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from pydantic import Field

from app.core.config import AppSettings, get_settings
from app.core.errors import AppError
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.uploaded_file_repository import UploadedFileRepository
from app.engine.template_requirement_service import TemplateRequirementService
from app.models.common import ContractModel
from app.models.enums import TaskStatus
from app.models.file_models import UploadedFileMeta, UploadedFileRecord
from app.models.task_models import OutputSummary, TaskMeta, TaskPaths, TaskRecord
from app.models.template_models import RequiredTable
from app.storage.file_manager import save_uploaded_file
from app.storage.paths import create_task_workspace


class CreateTaskRequest(ContractModel):
    task_name: str
    template_id: int = Field(ge=1)
    ai_enabled: bool = True


class CreateTaskResponse(ContractModel):
    task_id: str
    task_name: str
    template_id: int
    template_name: str
    status: TaskStatus
    task_dir: str
    required_tables: list[RequiredTable]
    created_at: datetime


class UploadTaskFileResponse(ContractModel):
    task_id: str
    table_name: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int = Field(ge=0)
    row_count: int = Field(default=0, ge=0)
    column_count: int = Field(default=0, ge=0)
    uploaded_at: datetime


class TaskService:
    def __init__(self, connection: sqlite3.Connection, settings: AppSettings | None = None) -> None:
        self.connection = connection
        self.settings = settings or get_settings()
        self.task_repository = TaskRepository(connection)
        self.uploaded_file_repository = UploadedFileRepository(connection)
        self.requirement_service = TemplateRequirementService(connection)

    def create_task(self, task_name: str, template_id: int, ai_enabled: bool = True) -> CreateTaskResponse:
        requirements = self.requirement_service.get_template_requirements(template_id)
        now = _utc_now()
        task_id = generate_task_id(now)
        workspace = create_task_workspace(task_id, self.settings)
        task_dir = _relative_path(workspace.task_dir, self.settings.project_root)

        task = TaskRecord(
            task_id=task_id,
            task_name=task_name,
            template_id=template_id,
            template_name=requirements.template_name,
            status=TaskStatus.CREATED,
            ai_enabled=ai_enabled,
            main_table=requirements.main_table,
            primary_key_field=requirements.primary_key_field,
            task_dir=task_dir,
            created_at=now,
            updated_at=now,
        )
        created = self.task_repository.create(task)
        meta = TaskMeta(
            task_id=created.task_id,
            task_name=created.task_name,
            template_id=created.template_id,
            template_name=created.template_name,
            template_file=requirements.template_file,
            ai_enabled=created.ai_enabled,
            status=created.status,
            main_table=requirements.main_table,
            main_table_cn=_main_table_cn(requirements),
            primary_key_field=requirements.primary_key_field,
            required_tables=requirements.required_tables,
            uploaded_files=[],
            output_summary=OutputSummary(),
            paths=TaskPaths(
                task_dir=task_dir,
                data_dir=_relative_path(workspace.data_dir, self.settings.project_root),
                output_dir=_relative_path(workspace.output_dir, self.settings.project_root),
                validation_dir=_relative_path(workspace.validation_dir, self.settings.project_root),
                logs_dir=_relative_path(workspace.logs_dir, self.settings.project_root),
            ),
            created_at=created.created_at,
            updated_at=created.updated_at,
        )
        write_task_meta(workspace.meta_path, meta)

        return CreateTaskResponse(
            task_id=created.task_id,
            task_name=created.task_name,
            template_id=created.template_id,
            template_name=created.template_name,
            status=created.status,
            task_dir=task_dir,
            required_tables=requirements.required_tables,
            created_at=created.created_at,
        )

    def upload_task_file(
        self,
        task_id: str,
        table_name: str,
        file_bytes: bytes,
        original_filename: str,
    ) -> UploadTaskFileResponse:
        if Path(original_filename).suffix.lower() != ".xlsx":
            raise AppError(
                code="UPLOAD_FILE_INVALID",
                message="Only .xlsx files are supported.",
                status_code=400,
                details={"filename": original_filename},
            )

        task = self.task_repository.get(task_id)
        if task is None:
            raise AppError(
                code="TASK_NOT_FOUND",
                message=f"Task not found: {task_id}",
                status_code=404,
                details={"task_id": task_id},
            )

        stored = save_uploaded_file(task_id, table_name, file_bytes, original_filename, self.settings)
        uploaded_at = _utc_now()
        file_path = _relative_path(stored.file_path, self.settings.project_root)
        record = UploadedFileRecord(
            task_id=task_id,
            table_name=stored.table_name,
            original_filename=original_filename,
            stored_filename=stored.stored_filename,
            path=file_path,
            file_path=file_path,
            file_size=stored.file_size,
            file_ext=".xlsx",
            row_count=0,
            column_count=0,
            checksum="",
            uploaded_at=uploaded_at,
        )
        saved = self.uploaded_file_repository.upsert(record)
        self.task_repository.update_status(task_id, TaskStatus.UPLOADED, updated_at=uploaded_at)
        self._update_meta_uploaded_files(task_id, uploaded_at)

        return UploadTaskFileResponse(
            task_id=saved.task_id,
            table_name=saved.table_name,
            original_filename=saved.original_filename,
            stored_filename=saved.stored_filename,
            file_path=saved.file_path,
            file_size=saved.file_size,
            row_count=saved.row_count,
            column_count=saved.column_count,
            uploaded_at=saved.uploaded_at,
        )

    def _update_meta_uploaded_files(self, task_id: str, updated_at: datetime) -> None:
        workspace = create_task_workspace(task_id, self.settings)
        if not workspace.meta_path.exists():
            return

        meta = TaskMeta.model_validate_json(workspace.meta_path.read_text(encoding="utf-8"))
        uploaded_files = self.uploaded_file_repository.list_by_task(task_id)
        meta = meta.model_copy(
            update={
                "status": TaskStatus.UPLOADED,
                "updated_at": updated_at,
                "uploaded_files": [
                    UploadedFileMeta(
                        table_name=item.table_name,
                        original_filename=item.original_filename,
                        stored_filename=item.stored_filename,
                        path=item.file_path,
                        row_count=item.row_count,
                        column_count=item.column_count,
                        uploaded_at=item.uploaded_at,
                    )
                    for item in uploaded_files
                ],
            }
        )
        write_task_meta(workspace.meta_path, meta)


def generate_task_id(now: datetime | None = None) -> str:
    current = now or _utc_now()
    return f"task_{current:%Y%m%d}_{current:%H%M%S}_{uuid4().hex[:6]}"


def write_task_meta(meta_path: Path, meta: TaskMeta) -> None:
    meta_path.write_text(
        json.dumps(meta.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _main_table_cn(requirements) -> str:
    for table in requirements.required_tables:
        if table.table_name == requirements.main_table:
            return table.table_name_cn
    return ""


def _relative_path(path: Path, project_root: Path) -> str:
    return Path(path).resolve().relative_to(project_root.resolve()).as_posix()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
