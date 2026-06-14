from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import AppError
from app.core.response import success_response
from app.db.connection import get_connection
from app.engine.template_requirement_service import TemplateRequirementService
from app.models.template_models import TemplateInfo

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
async def list_templates():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table,
                   output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
            FROM templates
            WHERE is_active = 1
            ORDER BY id ASC
            """
        ).fetchall()
        items = [_template_info(row).model_dump(mode="json") for row in rows]
    return success_response({"items": items, "total": len(items)})


@router.get("/{template_id}")
async def get_template(template_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, template_name, template_file, template_path, main_table,
                   output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
            FROM templates
            WHERE id = ?
            """,
            (template_id,),
        ).fetchone()
        if row is None:
            raise AppError("TEMPLATE_NOT_FOUND", f"Template not found: {template_id}", 404, {"template_id": template_id})
        item = _template_info(row).model_dump(mode="json")
    return success_response(item)


@router.get("/{template_id}/requirements")
async def get_template_requirements(template_id: int):
    with get_connection() as connection:
        requirements = TemplateRequirementService(connection).get_template_requirements(template_id)
    return success_response(requirements.model_dump(mode="json"))


def _template_info(row) -> TemplateInfo:
    return TemplateInfo(
        template_id=row["id"],
        template_name=row["template_name"],
        template_file=row["template_file"],
        template_path=row["template_path"],
        main_table=row["main_table"],
        output_name_pattern=row["output_name_pattern"],
        ai_enabled_default=bool(row["ai_enabled_default"]),
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
