from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.response import success_response
from app.db.connection import get_connection
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.task_repository import TaskRepository
from app.engine.data_loader import load_data_tables
from app.engine.template_requirement_service import TemplateRequirementService
from app.engine.validator import validate_task
from app.models.enums import TaskStatus, ValidationStatus
from app.models.task_models import TaskOutputsResponse
from app.models.validation_models import ValidateTaskResponse
from app.services.generation_service import GenerationService
from app.services.task_service import CreateTaskRequest, TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks():
    with get_connection() as connection:
        items = [task.model_dump(mode="json") for task in TaskRepository(connection).list()]
    return success_response({"items": items, "total": len(items)})


@router.post("")
async def create_task(request: CreateTaskRequest):
    with get_connection() as connection:
        result = TaskService(connection).create_task(
            task_name=request.task_name,
            template_id=request.template_id,
            ai_enabled=request.ai_enabled,
        )
    return success_response(result.model_dump(mode="json"))


@router.post("/{task_id}/upload")
async def upload_task_file(
    task_id: str,
    table_name: str = Form(...),
    file: UploadFile = File(...),
):
    file_bytes = await file.read()
    with get_connection() as connection:
        result = TaskService(connection).upload_task_file(
            task_id=task_id,
            table_name=table_name,
            file_bytes=file_bytes,
            original_filename=file.filename or "",
        )
    return success_response(result.model_dump(mode="json"))


@router.post("/{task_id}/validate")
async def validate_task_endpoint(task_id: str):
    settings = get_settings()
    with get_connection() as connection:
        task = TaskRepository(connection).get(task_id)
        if task is None:
            raise AppError("TASK_NOT_FOUND", f"Task not found: {task_id}", 404, {"task_id": task_id})

        requirements = TemplateRequirementService(connection).get_template_requirements(task.template_id)
        table_names = [table.table_name for table in requirements.required_tables]
        task_dir = settings.tasks_dir / task_id
        loaded_tables = load_data_tables(task_dir / "data", table_names)
        template_path = _resolve_project_path(requirements.template_path, settings.project_root)
        report = validate_task(
            task_id,
            requirements,
            loaded_tables,
            template_path,
            task_dir=task_dir,
            settings=settings,
        )

        status = TaskStatus.VALIDATION_FAILED if report.status == ValidationStatus.FAILED else TaskStatus.VALIDATED
        report_path = task_dir / "validation" / "validation_report.json"
        connection.execute(
            """
            UPDATE tasks
            SET status = ?, validation_report_path = ?, error_count = ?, warning_count = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (
                status.value,
                _relative_path(report_path, settings.project_root),
                report.summary.error_count,
                report.summary.warning_count,
                report.created_at.isoformat(),
                task_id,
            ),
        )
        response = ValidateTaskResponse(
            task_id=task_id,
            status=report.status,
            report_path=_relative_path(report_path, settings.project_root),
            summary=report.summary,
            items=report.items,
        )
    return success_response(response.model_dump(mode="json"))


@router.post("/{task_id}/generate")
async def generate_task_endpoint(task_id: str):
    with get_connection() as connection:
        result = GenerationService(connection).generate_task(task_id=task_id)
    return success_response(result.model_dump(mode="json"))


@router.get("/{task_id}/outputs")
async def list_task_outputs(task_id: str):
    with get_connection() as connection:
        task = TaskRepository(connection).get(task_id)
        if task is None:
            raise AppError("TASK_NOT_FOUND", f"Task not found: {task_id}", 404, {"task_id": task_id})
        documents = DocumentRepository(connection).list_by_task(task_id)
        response = TaskOutputsResponse(task_id=task_id, items=documents, total=len(documents))
    return success_response(response.model_dump(mode="json"))


@router.get("/{task_id}/download-zip")
async def download_task_zip(task_id: str):
    settings = get_settings()
    with get_connection() as connection:
        task = TaskRepository(connection).get(task_id)
        if task is None:
            raise AppError("TASK_NOT_FOUND", f"Task not found: {task_id}", 404, {"task_id": task_id})
        documents = DocumentRepository(connection).list_by_task(task_id)

    temp_dir = settings.temp_dir / task_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = temp_dir / f"{task_id}_outputs.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            if document.status != "success":
                continue
            source_path = _resolve_project_path(document.output_path, settings.project_root)
            if source_path.exists() and source_path.is_file():
                archive.write(source_path, arcname=document.output_filename)

    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_path.name,
    )


def _resolve_project_path(path_value: str, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path


def _relative_path(path: Path, project_root: Path) -> str:
    return Path(path).resolve().relative_to(project_root.resolve()).as_posix()
