from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from app.core.config import AppSettings, get_settings
from app.core.errors import AppError
from app.db.repositories.field_repository import FieldRepository
from app.models.enums import DataType
from app.models.settings_models import (
    EntitySchemaImportItem,
    EntitySchemaImportPreview,
    EntitySchemaImportSummary,
)
from app.models.template_models import FieldDefinition

REQUIRED_IMPORT_COLUMNS = {"table_name", "table_name_cn", "field_name", "field_name_cn"}
OPTIONAL_IMPORT_DEFAULTS: dict[str, Any] = {
    "data_type": DataType.STRING.value,
    "is_primary_key": False,
    "required": False,
    "display_format": "",
    "description": "",
}
BOOL_TRUE_VALUES = {"1", "true", "yes", "y", "是", "对", "是的"}
BOOL_FALSE_VALUES = {"0", "false", "no", "n", "否", "错", ""}


class EntitySchemaService:
    def __init__(self, repository: FieldRepository, settings: AppSettings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def list_fields(
        self,
        table_name: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return self.repository.list_fields(table_name=table_name, keyword=keyword, page=page, page_size=page_size)

    def preview_import(self, original_filename: str, file_bytes: bytes) -> EntitySchemaImportPreview:
        if Path(original_filename).suffix.lower() != ".xlsx":
            raise AppError("UPLOAD_FILE_INVALID", "仅支持上传 entity_schema.xlsx 文件", 400)

        import_id = f"tmp_{uuid4().hex}"
        items: list[EntitySchemaImportItem] = []
        fields: list[FieldDefinition] = []
        field_row_numbers: dict[tuple[str, str], int] = {}
        skip_count = 0

        try:
            dataframe = pd.read_excel(BytesIO(file_bytes), sheet_name=0)
        except Exception as exc:
            raise AppError("UPLOAD_FILE_INVALID", "无法读取 entity_schema.xlsx 文件", 400) from exc

        missing_columns = REQUIRED_IMPORT_COLUMNS - set(dataframe.columns)
        if missing_columns:
            items.append(
                EntitySchemaImportItem(
                    row_number=1,
                    action="error",
                    level="error",
                    message=f"缺少必需列：{', '.join(sorted(missing_columns))}",
                )
            )
            preview = self._build_preview(import_id, total_rows=len(dataframe), fields=[], items=items, skip_count=0)
            self._save_preview(import_id, preview, fields)
            return preview

        normalized = dataframe.copy()
        for column, default in OPTIONAL_IMPORT_DEFAULTS.items():
            if column not in normalized.columns:
                normalized[column] = default

        seen_keys: dict[tuple[str, str], int] = {}
        table_cn_by_table: dict[str, str] = {}
        table_by_table_cn: dict[str, str] = {}
        field_cn_by_table: dict[str, set[str]] = {}
        primary_key_counts: dict[str, int] = {}

        for index, row in normalized.iterrows():
            row_number = int(index) + 2
            field, row_errors = self._parse_row(row.to_dict())
            if field is None:
                for message in row_errors:
                    items.append(EntitySchemaImportItem(row_number=row_number, action="error", level="error", message=message))
                continue

            key = (field.table_name, field.field_name)
            if key in seen_keys:
                row_errors.append(f"同一 table_name + field_name 不允许重复：{field.table_name}.{field.field_name}")
            else:
                seen_keys[key] = row_number

            if field.table_name_cn:
                existing_cn = table_cn_by_table.get(field.table_name)
                if existing_cn and existing_cn != field.table_name_cn:
                    row_errors.append(f"中文表名映射冲突：{field.table_name} 同时映射到 {existing_cn} 和 {field.table_name_cn}")
                table_cn_by_table[field.table_name] = field.table_name_cn

                existing_table = table_by_table_cn.get(field.table_name_cn)
                if existing_table and existing_table != field.table_name:
                    row_errors.append(f"中文表名映射冲突：{field.table_name_cn} 同时映射到 {existing_table} 和 {field.table_name}")
                table_by_table_cn[field.table_name_cn] = field.table_name

            if field.field_name_cn:
                table_field_names = field_cn_by_table.setdefault(field.table_name, set())
                if field.field_name_cn in table_field_names:
                    row_errors.append(f"同一表内中文字段名不能重复：{field.table_name}.{field.field_name_cn}")
                table_field_names.add(field.field_name_cn)

            if field.is_primary_key:
                primary_key_counts[field.table_name] = primary_key_counts.get(field.table_name, 0) + 1

            if row_errors:
                for message in row_errors:
                    items.append(EntitySchemaImportItem(row_number=row_number, action="error", level="error", message=message))
                continue

            fields.append(field)
            field_row_numbers[(field.table_name, field.field_name)] = row_number

        for table_name, count in sorted(primary_key_counts.items()):
            if count > 1:
                items.append(
                    EntitySchemaImportItem(
                        row_number=1,
                        action="error",
                        level="error",
                        message=f"同一 table_name 只能有一个主键：{table_name}",
                    )
                )

        self._append_existing_mapping_conflicts(fields, items)
        existing_keys = self.repository.get_existing_keys()
        for field in fields:
            action = "update" if (field.table_name, field.field_name) in existing_keys else "create"
            items.append(
                EntitySchemaImportItem(
                    row_number=field_row_numbers.get((field.table_name, field.field_name), 1),
                    action=action,
                    level="info",
                    message=(
                        f"将更新字段 {field.table_name}.{field.field_name}"
                        if action == "update"
                        else f"将新增字段 {field.table_name}.{field.field_name}"
                    ),
                )
            )

        preview = self._build_preview(import_id, total_rows=len(normalized), fields=fields, items=items, skip_count=skip_count)
        self._save_preview(import_id, preview, fields)
        return preview

    def commit_import(self, import_id: str, mode: str) -> EntitySchemaImportPreview:
        if mode != "upsert":
            raise AppError("BAD_REQUEST", "仅支持 upsert 导入模式", 400)
        payload = self._load_preview(import_id)
        preview = EntitySchemaImportPreview(**payload["preview"])
        if not preview.can_commit:
            raise AppError("VALIDATION_FAILED", "导入预校验存在错误，不能提交", 400, {"import_id": import_id})
        fields = [FieldDefinition(**item) for item in payload["fields"]]
        self.repository.upsert_fields(fields, self._now())
        return preview

    def export_excel(self) -> bytes:
        rows = [
            {
                "table_name": field.table_name,
                "table_name_cn": field.table_name_cn,
                "field_name": field.field_name,
                "field_name_cn": field.field_name_cn,
                "data_type": self._data_type_value(field),
                "is_primary_key": field.is_primary_key,
                "required": field.required,
                "display_format": field.display_format,
                "description": field.description,
            }
            for field in self.repository.export_fields()
        ]
        buffer = BytesIO()
        pd.DataFrame(rows).to_excel(buffer, index=False)
        return buffer.getvalue()

    def _parse_row(self, row: dict[str, Any]) -> tuple[FieldDefinition | None, list[str]]:
        errors: list[str] = []
        table_name = self._clean_text(row.get("table_name"))
        table_name_cn = self._clean_text(row.get("table_name_cn"))
        field_name = self._clean_text(row.get("field_name"))
        field_name_cn = self._clean_text(row.get("field_name_cn"))
        if not table_name:
            errors.append("table_name 不能为空")
        if not table_name_cn:
            errors.append("table_name_cn 不能为空")
        if not field_name:
            errors.append("field_name 不能为空")
        if not field_name_cn:
            errors.append("field_name_cn 不能为空")

        data_type = self._clean_text(row.get("data_type")) or DataType.STRING.value
        try:
            parsed_data_type = DataType(data_type)
        except ValueError:
            errors.append(f"data_type 不在允许范围内：{data_type}")
            parsed_data_type = DataType.STRING

        is_primary_key = self._parse_bool(row.get("is_primary_key"), "is_primary_key", errors)
        required = self._parse_bool(row.get("required"), "required", errors)
        if errors:
            return None, errors

        return (
            FieldDefinition(
                table_name=table_name,
                table_name_cn=table_name_cn,
                field_name=field_name,
                field_name_cn=field_name_cn,
                data_type=parsed_data_type,
                is_primary_key=is_primary_key,
                required=required,
                display_format=self._clean_text(row.get("display_format")),
                description=self._clean_text(row.get("description")),
            ),
            [],
        )

    def _append_existing_mapping_conflicts(
        self,
        fields: list[FieldDefinition],
        items: list[EntitySchemaImportItem],
    ) -> None:
        existing_fields = self.repository.export_fields()
        imported_keys = {(field.table_name, field.field_name) for field in fields}
        table_cn_by_table: dict[str, str] = {}
        table_by_table_cn: dict[str, str] = {}
        field_cn_by_table: dict[str, set[str]] = {}

        for field in existing_fields:
            if (field.table_name, field.field_name) in imported_keys:
                continue
            if field.table_name_cn:
                table_cn_by_table.setdefault(field.table_name, field.table_name_cn)
                table_by_table_cn.setdefault(field.table_name_cn, field.table_name)
            if field.field_name_cn:
                field_cn_by_table.setdefault(field.table_name, set()).add(field.field_name_cn)

        for field in fields:
            if field.table_name_cn:
                existing_cn = table_cn_by_table.get(field.table_name)
                if existing_cn and existing_cn != field.table_name_cn:
                    items.append(EntitySchemaImportItem(row_number=1, action="error", level="error", message=f"与现有中文表名映射冲突：{field.table_name} 已映射到 {existing_cn}"))
                existing_table = table_by_table_cn.get(field.table_name_cn)
                if existing_table and existing_table != field.table_name:
                    items.append(EntitySchemaImportItem(row_number=1, action="error", level="error", message=f"与现有中文表名映射冲突：{field.table_name_cn} 已映射到 {existing_table}"))
            if field.field_name_cn and field.field_name_cn in field_cn_by_table.get(field.table_name, set()):
                items.append(EntitySchemaImportItem(row_number=1, action="error", level="error", message=f"与现有中文字段名冲突：{field.table_name}.{field.field_name_cn}"))

    def _build_preview(
        self,
        import_id: str,
        total_rows: int,
        fields: list[FieldDefinition],
        items: list[EntitySchemaImportItem],
        skip_count: int,
    ) -> EntitySchemaImportPreview:
        create_count = sum(1 for item in items if item.action == "create")
        update_count = sum(1 for item in items if item.action == "update")
        error_count = sum(1 for item in items if item.level == "error")
        warning_count = sum(1 for item in items if item.level == "warning")
        return EntitySchemaImportPreview(
            import_id=import_id,
            summary=EntitySchemaImportSummary(
                total_rows=total_rows,
                create_count=create_count,
                update_count=update_count,
                skip_count=skip_count,
                error_count=error_count,
                warning_count=warning_count,
            ),
            items=items,
            can_commit=error_count == 0,
        )

    def _save_preview(self, import_id: str, preview: EntitySchemaImportPreview, fields: list[FieldDefinition]) -> None:
        self._preview_dir().mkdir(parents=True, exist_ok=True)
        payload = {
            "preview": preview.model_dump(mode="json"),
            "fields": [field.model_dump(mode="json") for field in fields],
        }
        self._preview_path(import_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_preview(self, import_id: str) -> dict[str, Any]:
        if not import_id.startswith("tmp_"):
            raise AppError("BAD_REQUEST", "import_id 无效", 400)
        path = self._preview_path(import_id)
        if not path.exists():
            raise AppError("FILE_NOT_FOUND", "导入预览结果不存在或已过期", 404, {"import_id": import_id})
        return json.loads(path.read_text(encoding="utf-8"))

    def _preview_dir(self) -> Path:
        return self.settings.temp_dir / "entity_schema_imports"

    def _preview_path(self, import_id: str) -> Path:
        return self._preview_dir() / f"{import_id}.json"

    def _clean_text(self, value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    def _parse_bool(self, value: Any, column: str, errors: list[str]) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        cleaned = str(value).strip().lower()
        if cleaned in BOOL_TRUE_VALUES:
            return True
        if cleaned in BOOL_FALSE_VALUES:
            return False
        errors.append(f"{column} 无法解析为 boolean：{value}")
        return False

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _data_type_value(self, field: Any) -> str:
        return field.data_type.value if hasattr(field.data_type, "value") else str(field.data_type)
