from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from docx import Document

from app.core.config import AppSettings, get_settings
from app.core.errors import AppError
from app.db.repositories.template_repository import TemplateRepository
from app.models.settings_models import TemplateFileRecord
from app.storage.file_manager import save_template_file
from app.storage.paths import ensure_path_under_base
from app.storage.safe_filename import safe_template_filename


class TemplateFileService:
    def __init__(self, repository: TemplateRepository, settings: AppSettings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def list_template_files(self) -> list[TemplateFileRecord]:
        return self.repository.list_template_files()

    def create_template_file(
        self,
        template_name: str,
        description: str,
        original_filename: str,
        file_bytes: bytes,
    ) -> TemplateFileRecord:
        cleaned_name = template_name.strip()
        if not cleaned_name:
            raise AppError("BAD_REQUEST", "模板名称不能为空", 400)
        if Path(original_filename).suffix.lower() != ".docx":
            raise AppError("UPLOAD_FILE_INVALID", "仅支持上传 .docx 模板文件", 400)

        self._validate_docx(file_bytes)

        now = self._now()
        placeholder_file = f"pending_{uuid4().hex}.docx"
        template_id = self.repository.create_template_file_placeholder(
            template_name=cleaned_name,
            original_filename=original_filename,
            description=description.strip(),
            now=now,
            placeholder_file=placeholder_file,
        )
        stored_filename = safe_template_filename(template_id)
        template_path = f"templates/{stored_filename}"

        try:
            save_template_file(template_id, file_bytes, self.settings)
            self.repository.update_template_file_path(template_id, stored_filename, template_path, self._now())
        except FileExistsError as exc:
            self.repository.delete_template_metadata(template_id)
            raise AppError("UPLOAD_FILE_INVALID", "模板系统文件名已存在，未覆盖已有文件", 400) from exc
        except Exception:
            self.repository.delete_template_metadata(template_id)
            raise

        record = self.repository.get_template_file(template_id)
        if record is None:
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        return record

    def get_download_path(self, template_id: int) -> tuple[Path, TemplateFileRecord]:
        record = self.repository.get_template_file(template_id)
        if record is None:
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        path = self._resolve_template_path(record.template_path)
        if not path.exists() or not path.is_file():
            raise AppError("FILE_NOT_FOUND", f"Template file not found: {template_id}", 404, {"template_id": template_id})
        return path, record

    def deactivate_template_file(self, template_id: int) -> TemplateFileRecord:
        if not self.repository.deactivate_template(template_id, self._now()):
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        record = self.repository.get_template_file(template_id)
        if record is None:
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        return record

    def _validate_docx(self, file_bytes: bytes) -> None:
        try:
            Document(BytesIO(file_bytes))
        except Exception as exc:
            raise AppError("UPLOAD_FILE_INVALID", "上传文件不是有效的 .docx 模板文件", 400) from exc

    def _resolve_template_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if not path.is_absolute():
            path = self.settings.project_root / path
        return ensure_path_under_base(path, self.settings.templates_dir)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
