from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import get_settings
from app.core.response import success_response
from app.db.connection import get_connection
from app.db.repositories.ai_config_repository import AIConfigRepository
from app.db.repositories.field_repository import FieldRepository
from app.db.repositories.template_table_repository import TemplateTableRepository
from app.models.settings_models import (
    EntitySchemaImportCommitRequest,
    AIConfigUpdateRequest,
    SettingsHealth,
    TemplateRelationImportCommitRequest,
)
from app.db.repositories.template_repository import TemplateRepository
from app.engine.template_file_type import media_type_for_file
from app.services.entity_schema_service import EntitySchemaService
from app.services.ai_config_service import AIConfigService
from app.services.template_relation_service import TemplateRelationService
from app.services.template_file_service import TemplateFileService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/health")
async def settings_health():
    return success_response(SettingsHealth(status="ok").model_dump(mode="json"))


@router.get("/template-files")
async def list_template_files():
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        items = [item.model_dump(mode="json") for item in service.list_template_files()]
    return success_response({"items": items, "total": len(items)})


@router.post("/template-files")
async def upload_template_file(
    template_name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
):
    file_bytes = await file.read()
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        record = service.create_template_file(
            template_name=template_name,
            description=description,
            original_filename=file.filename or "",
            file_bytes=file_bytes,
        )
    return success_response(record.model_dump(mode="json"))


@router.get("/template-files/{template_id}/download")
async def download_template_file(template_id: int):
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        path, record = service.get_download_path(template_id)
    return FileResponse(
        path,
        media_type=media_type_for_file(path),
        filename=record.original_filename,
    )


@router.delete("/template-files/{template_id}")
async def deactivate_template_file(template_id: int):
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        record = service.deactivate_template_file(template_id)
    return success_response(record.model_dump(mode="json"))


@router.post("/template-files/{template_id}/activate")
async def activate_template_file(template_id: int):
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        record = service.activate_template_file(template_id)
    return success_response(record.model_dump(mode="json"))


@router.put("/template-files/{template_id}/file")
async def replace_template_file(template_id: int, file: UploadFile = File(...)):
    file_bytes = await file.read()
    with get_connection() as connection:
        service = TemplateFileService(TemplateRepository(connection), get_settings())
        record = service.replace_template_file(
            template_id=template_id,
            original_filename=file.filename or "",
            file_bytes=file_bytes,
        )
    return success_response(record.model_dump(mode="json"))


@router.get("/entity-schema")
async def list_entity_schema(
    table_name: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    with get_connection() as connection:
        service = EntitySchemaService(FieldRepository(connection), get_settings())
        items, total = service.list_fields(table_name=table_name, keyword=keyword, page=page, page_size=page_size)
    return success_response({"items": [item.model_dump(mode="json") for item in items], "total": total})


@router.get("/entity-schema/tables")
async def list_entity_schema_tables(keyword: str | None = None):
    with get_connection() as connection:
        repository = FieldRepository(connection)
        items = repository.list_table_summaries(keyword=keyword)
    return success_response({"items": [item.model_dump(mode="json") for item in items], "total": len(items)})


@router.post("/entity-schema/import/preview")
async def preview_entity_schema_import(file: UploadFile = File(...)):
    file_bytes = await file.read()
    with get_connection() as connection:
        service = EntitySchemaService(FieldRepository(connection), get_settings())
        preview = service.preview_import(file.filename or "", file_bytes)
    return success_response(preview.model_dump(mode="json"))


@router.post("/entity-schema/import/commit")
async def commit_entity_schema_import(payload: EntitySchemaImportCommitRequest):
    with get_connection() as connection:
        service = EntitySchemaService(FieldRepository(connection), get_settings())
        preview = service.commit_import(payload.import_id, payload.mode)
    return success_response(preview.model_dump(mode="json"))


@router.get("/entity-schema/export")
async def export_entity_schema():
    with get_connection() as connection:
        service = EntitySchemaService(FieldRepository(connection), get_settings())
        content = service.export_excel()
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="entity_schema.xlsx"'},
    )


@router.get("/template-relations")
async def list_template_relations(
    template_id: int | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    with get_connection() as connection:
        service = TemplateRelationService(
            TemplateRepository(connection),
            TemplateTableRepository(connection),
            FieldRepository(connection),
            get_settings(),
        )
        items, total = service.list_relations(
            template_id=template_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
    return success_response({"items": [item.model_dump(mode="json") for item in items], "total": total})


@router.post("/template-relations/import/preview")
async def preview_template_relation_import(file: UploadFile = File(...)):
    file_bytes = await file.read()
    with get_connection() as connection:
        service = TemplateRelationService(
            TemplateRepository(connection),
            TemplateTableRepository(connection),
            FieldRepository(connection),
            get_settings(),
        )
        preview = service.preview_import(file.filename or "", file_bytes)
    return success_response(preview.model_dump(mode="json"))


@router.post("/template-relations/import/commit")
async def commit_template_relation_import(payload: TemplateRelationImportCommitRequest):
    with get_connection() as connection:
        service = TemplateRelationService(
            TemplateRepository(connection),
            TemplateTableRepository(connection),
            FieldRepository(connection),
            get_settings(),
        )
        preview = service.commit_import(payload.import_id, payload.mode)
    return success_response(preview.model_dump(mode="json"))


@router.get("/template-relations/export")
async def export_template_relations():
    with get_connection() as connection:
        service = TemplateRelationService(
            TemplateRepository(connection),
            TemplateTableRepository(connection),
            FieldRepository(connection),
            get_settings(),
        )
        content = service.export_excel()
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="template_relation.xlsx"'},
    )


@router.get("/ai-config")
async def get_ai_config():
    with get_connection() as connection:
        service = AIConfigService(AIConfigRepository(connection), get_settings())
        config = service.get_config()
    return success_response(config.model_dump(mode="json"))


@router.put("/ai-config")
async def update_ai_config(payload: AIConfigUpdateRequest):
    with get_connection() as connection:
        service = AIConfigService(AIConfigRepository(connection), get_settings())
        config = service.update_config(payload)
    return success_response(config.model_dump(mode="json"))


@router.post("/ai-config/test")
async def test_ai_config():
    with get_connection() as connection:
        service = AIConfigService(AIConfigRepository(connection), get_settings())
        result = service.test_connection()
    return success_response(result.model_dump(mode="json"))
