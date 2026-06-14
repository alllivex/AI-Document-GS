from __future__ import annotations

import re
from pathlib import Path

from pydantic import Field

from app.core.config import AppSettings, get_settings
from app.models.common import ContractModel
from app.storage.safe_filename import has_path_traversal

SAFE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")


class CreateTaskWorkspaceInput(ContractModel):
    task_id: str


class TaskWorkspace(ContractModel):
    task_id: str
    task_dir: Path
    data_dir: Path
    output_dir: Path
    validation_dir: Path
    logs_dir: Path
    temp_dir: Path
    meta_path: Path


def validate_safe_segment(value: str, field_name: str) -> str:
    if has_path_traversal(value) or not SAFE_SEGMENT_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} contains unsafe path characters: {value}")
    return value


def ensure_path_under_base(path: Path, base_dir: Path) -> Path:
    resolved_base = base_dir.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_base)
    except ValueError as exc:
        raise ValueError(f"path escapes base directory: {resolved_path}") from exc
    return resolved_path


def build_task_workspace(task_id: str, settings: AppSettings | None = None) -> TaskWorkspace:
    safe_task_id = validate_safe_segment(task_id, "task_id")
    current_settings = settings or get_settings()

    task_dir = ensure_path_under_base(current_settings.tasks_dir / safe_task_id, current_settings.tasks_dir)
    temp_dir = ensure_path_under_base(current_settings.temp_dir / safe_task_id, current_settings.temp_dir)

    return TaskWorkspace(
        task_id=safe_task_id,
        task_dir=task_dir,
        data_dir=task_dir / "data",
        output_dir=task_dir / "output",
        validation_dir=task_dir / "validation",
        logs_dir=task_dir / "logs",
        temp_dir=temp_dir,
        meta_path=task_dir / "meta.json",
    )


def create_task_workspace(task_id: str, settings: AppSettings | None = None) -> TaskWorkspace:
    workspace = build_task_workspace(task_id, settings)
    for directory in (
        workspace.task_dir,
        workspace.data_dir,
        workspace.output_dir,
        workspace.validation_dir,
        workspace.logs_dir,
        workspace.temp_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return workspace


def get_upload_file_path(task_id: str, table_name: str, settings: AppSettings | None = None) -> Path:
    safe_table_name = validate_safe_segment(table_name, "table_name")
    workspace = build_task_workspace(task_id, settings)
    file_path = workspace.data_dir / f"{safe_table_name}.xlsx"
    return ensure_path_under_base(file_path, workspace.data_dir)
