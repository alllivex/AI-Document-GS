from __future__ import annotations

import sqlite3

from app.core.errors import AppError
from app.db.repositories.template_repository import TemplateRepository
from app.models.template_models import TemplateDetail, TemplateListItem


class TemplateService:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.repository = TemplateRepository(connection)

    def list_templates(self, search: str | None = None, active_only: bool = True) -> list[TemplateListItem]:
        return self.repository.list_templates(search=search, active_only=active_only)

    def get_template_detail(self, template_id: int) -> TemplateDetail:
        detail = self.repository.get_template_detail(template_id)
        if detail is None:
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        return detail
