from __future__ import annotations

from pathlib import Path

from pydantic import Field

from app.core.config import AppSettings, get_settings
from app.models.common import ContractModel
from app.storage.paths import create_task_workspace, get_upload_file_path, validate_safe_segment
from app.storage.safe_filename import safe_template_filename


class SaveUploadInput(ContractModel):
    task_id: str
    table_name: str
    original_filename: str
    file_bytes: bytes


class StoredFileInfo(ContractModel):
    table_name: str
    original_filename: str
    stored_filename: str
    file_path: Path
    file_size: int = Field(ge=0)


def save_uploaded_file(
    task_id: str,
    table_name: str,
    file_bytes: bytes,
    original_filename: str,
    settings: AppSettings | None = None,
) -> StoredFileInfo:
    safe_table_name = validate_safe_segment(table_name, "table_name")
    create_task_workspace(task_id, settings)
    file_path = get_upload_file_path(task_id, safe_table_name, settings)
    file_path.write_bytes(file_bytes)

    return StoredFileInfo(
        table_name=safe_table_name,
        original_filename=original_filename,
        stored_filename=f"{safe_table_name}.xlsx",
        file_path=file_path,
        file_size=len(file_bytes),
    )


def save_template_file(
    template_id: int,
    file_bytes: bytes,
    settings: AppSettings | None = None,
    suffix: str = ".docx",
) -> StoredFileInfo:
    current_settings = settings or get_settings()
    current_settings.templates_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = safe_template_filename(template_id, suffix)
    file_path = current_settings.templates_dir / stored_filename
    if file_path.exists():
        raise FileExistsError(f"template file already exists: {stored_filename}")
    file_path.write_bytes(file_bytes)

    return StoredFileInfo(
        table_name="",
        original_filename=stored_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=len(file_bytes),
    )
