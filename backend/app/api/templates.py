from __future__ import annotations

from fastapi import APIRouter

from app.core.response import success_response
from app.db.connection import get_connection
from app.engine.template_requirement_service import TemplateRequirementService
from app.services.template_service import TemplateService

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates(search: str | None = None, active_only: bool = True):
    with get_connection() as connection:
        items = [
            item.model_dump(mode="json")
            for item in TemplateService(connection).list_templates(search=search, active_only=active_only)
        ]
    return success_response({"items": items, "total": len(items)})


@router.get("/{template_id}")
async def get_template(template_id: int):
    with get_connection() as connection:
        detail = TemplateService(connection).get_template_detail(template_id)
    return success_response(detail.model_dump(mode="json"))


@router.get("/{template_id}/requirements")
async def get_template_requirements(template_id: int):
    with get_connection() as connection:
        requirements = TemplateRequirementService(connection).get_template_requirements(template_id)
    return success_response(requirements.model_dump(mode="json"))
