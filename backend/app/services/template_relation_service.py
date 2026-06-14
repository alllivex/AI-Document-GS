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
from app.db.repositories.template_repository import TemplateRepository
from app.db.repositories.template_table_repository import TemplateTableRepository
from app.models.enums import RelationType, TableRole
from app.models.settings_models import (
    TemplateRelationImportItem,
    TemplateRelationImportPreview,
    TemplateRelationImportSummary,
)

REQUIRED_COLUMNS = {"template_file", "table_name", "role", "relation_type"}
OPTIONAL_DEFAULTS: dict[str, Any] = {
    "template_id": "",
    "template_name": "",
    "table_name_cn": "",
    "main_join_key": "",
    "table_join_key": "",
    "required": True,
    "sort_order": 0,
    "description": "",
}
TRUE_VALUES = {"1", "true", "yes", "y", "是", "对"}
FALSE_VALUES = {"0", "false", "no", "n", "否", "错", ""}


class TemplateRelationService:
    def __init__(
        self,
        template_repository: TemplateRepository,
        template_table_repository: TemplateTableRepository,
        field_repository: FieldRepository,
        settings: AppSettings | None = None,
    ) -> None:
        self.template_repository = template_repository
        self.template_table_repository = template_table_repository
        self.field_repository = field_repository
        self.settings = settings or get_settings()

    def list_relations(
        self,
        template_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        return self.template_table_repository.list_relations(
            template_id=template_id,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def preview_import(self, original_filename: str, file_bytes: bytes) -> TemplateRelationImportPreview:
        if Path(original_filename).suffix.lower() != ".xlsx":
            raise AppError("UPLOAD_FILE_INVALID", "仅支持上传 template_relation.xlsx 文件", 400)
        try:
            dataframe = pd.read_excel(BytesIO(file_bytes), sheet_name=0)
        except Exception as exc:
            raise AppError("UPLOAD_FILE_INVALID", "无法读取 template_relation.xlsx 文件", 400) from exc

        import_id = f"tmp_{uuid4().hex}"
        items: list[TemplateRelationImportItem] = []
        missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)
        if "template_id" not in dataframe.columns and "template_name" not in dataframe.columns:
            missing_columns.add("template_id 或 template_name")
        if missing_columns:
            items.append(
                TemplateRelationImportItem(
                    row_number=1,
                    action="error",
                    level="error",
                    message=f"缺少必需列：{', '.join(sorted(missing_columns))}",
                )
            )
            preview = self._build_preview(import_id, len(dataframe), items)
            self._save_preview(import_id, preview, [])
            return preview

        normalized = dataframe.copy()
        for column, default in OPTIONAL_DEFAULTS.items():
            if column not in normalized.columns:
                normalized[column] = default

        rows: list[dict[str, Any]] = []
        grouped: dict[str, list[dict[str, Any]]] = {}
        seen_relation_keys: set[tuple[str, str]] = set()
        table_names = self.field_repository.table_names()
        field_names_by_table = self.field_repository.field_names_by_table()

        for index, raw_row in normalized.iterrows():
            row_number = int(index) + 2
            row, row_errors = self._parse_row(raw_row.to_dict(), row_number)
            if row:
                relation_key = (row["template_key"], row["table_name"])
                if relation_key in seen_relation_keys:
                    row_errors.append(f"同一模板内 table_name 不允许重复：{row['table_name']}")
                seen_relation_keys.add(relation_key)

                if row["template_id"] and not row["template_name"] and not self.template_repository.get_template_row(row["template_id"]):
                    row_errors.append("创建新模板记录时 template_name 必填")
                if row["table_name"] not in table_names:
                    row_errors.append(f"table_name 不存在于 fields 表：{row['table_name']}")
                if not self._template_file_is_known(row["template_file"]):
                    row_errors.append(f"template_file 不存在于 templates 表或 templates/ 目录：{row['template_file']}")

            if row_errors:
                for message in row_errors:
                    items.append(TemplateRelationImportItem(row_number=row_number, action="error", level="error", message=message))
                continue

            rows.append(row)
            grouped.setdefault(row["template_key"], []).append(row)

        for template_rows in grouped.values():
            main_rows = [row for row in template_rows if row["role"] == TableRole.MAIN.value]
            if len(main_rows) != 1:
                label = template_rows[0]["template_label"]
                items.append(
                    TemplateRelationImportItem(
                        row_number=template_rows[0]["row_number"],
                        action="error",
                        level="error",
                        message=f"每个模板必须且只能有一个主表：{label}",
                    )
                )
                continue

            main_row = main_rows[0]
            main_table = main_row["table_name"]
            for row in template_rows:
                if row["role"] == TableRole.MAIN.value and row["relation_type"] != RelationType.MAIN.value:
                    items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message="main 表 relation_type 必须是 main"))
                if row["role"] == TableRole.AUX.value:
                    if row["relation_type"] == RelationType.MAIN.value:
                        items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message="aux 表 relation_type 不能是 main"))
                    if not row["main_join_key"]:
                        items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message="aux 表 main_join_key 必填"))
                    if not row["table_join_key"]:
                        items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message="aux 表 table_join_key 必填"))
                    if row["main_join_key"] and row["main_join_key"] not in field_names_by_table.get(main_table, set()):
                        items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message=f"main_join_key 不存在于主表字段中：{main_table}.{row['main_join_key']}"))
                    if row["table_join_key"] and row["table_join_key"] not in field_names_by_table.get(row["table_name"], set()):
                        items.append(TemplateRelationImportItem(row_number=row["row_number"], action="error", level="error", message=f"table_join_key 不存在于当前表字段中：{row['table_name']}.{row['table_join_key']}"))

        existing_relation_keys = self.template_table_repository.existing_keys()
        for row in rows:
            resolved_template_id = self._preview_template_id(row)
            action = "update" if resolved_template_id and (resolved_template_id, row["table_name"]) in existing_relation_keys else "create"
            items.append(
                TemplateRelationImportItem(
                    row_number=row["row_number"],
                    action=action,
                    level="info",
                    message=(
                        f"将更新模板关系：{row['template_name']} - {row['table_name_cn'] or row['table_name']}"
                        if action == "update"
                        else f"将新增模板关系：{row['template_name']} - {row['table_name_cn'] or row['table_name']}"
                    ),
                )
            )

        preview = self._build_preview(import_id, len(normalized), items)
        self._save_preview(import_id, preview, rows)
        return preview

    def commit_import(self, import_id: str, mode: str) -> TemplateRelationImportPreview:
        if mode != "upsert":
            raise AppError("BAD_REQUEST", "仅支持 upsert 导入模式", 400)
        payload = self._load_preview(import_id)
        preview = TemplateRelationImportPreview(**payload["preview"])
        if not preview.can_commit:
            raise AppError("VALIDATION_FAILED", "导入预校验存在错误，不能提交", 400, {"import_id": import_id})

        rows = payload["rows"]
        now = self._now()
        template_id_by_key: dict[str, int] = {}
        for template_key, template_rows in self._group_rows(rows).items():
            main_row = next(row for row in template_rows if row["role"] == TableRole.MAIN.value)
            template_id_by_key[template_key] = self._resolve_or_create_template(main_row, now)

        for row in rows:
            template_id = template_id_by_key[row["template_key"]]
            self.template_table_repository.upsert_relation(
                template_id=template_id,
                table_name=row["table_name"],
                table_name_cn=row["table_name_cn"],
                role=row["role"],
                relation_type=row["relation_type"],
                main_join_key=row["main_join_key"],
                table_join_key=row["table_join_key"],
                required=bool(row["required"]),
                sort_order=int(row["sort_order"]),
                description=row["description"],
                now=now,
            )
        return preview

    def export_excel(self) -> bytes:
        rows = [
            {
                "template_id": relation.template_id,
                "template_name": relation.template_name,
                "template_file": relation.template_file,
                "table_name": relation.table_name,
                "table_name_cn": relation.table_name_cn,
                "role": relation.role,
                "relation_type": relation.relation_type,
                "main_join_key": relation.main_join_key,
                "table_join_key": relation.table_join_key,
                "required": relation.required,
                "description": relation.description,
            }
            for relation in self.template_table_repository.export_relations()
        ]
        buffer = BytesIO()
        pd.DataFrame(rows).to_excel(buffer, index=False)
        return buffer.getvalue()

    def _parse_row(self, row: dict[str, Any], row_number: int) -> tuple[dict[str, Any] | None, list[str]]:
        errors: list[str] = []
        template_id = self._parse_template_id(row.get("template_id"), errors)
        template_name = self._clean_text(row.get("template_name"))
        template_file = self._clean_text(row.get("template_file"))
        table_name = self._clean_text(row.get("table_name"))
        table_name_cn = self._clean_text(row.get("table_name_cn"))
        role_value = self._clean_text(row.get("role")).lower()
        relation_type_value = self._clean_text(row.get("relation_type")).lower()
        if template_id is None and not template_name:
            errors.append("template_id 或 template_name 必须至少填写一个")
        if not template_file:
            errors.append("template_file 不能为空")
        if not table_name:
            errors.append("table_name 不能为空")
        if role_value not in {item.value for item in TableRole}:
            errors.append(f"role 只能是 main 或 aux：{role_value}")
        if relation_type_value not in {item.value for item in RelationType}:
            errors.append(f"relation_type 不在允许范围内：{relation_type_value}")
        required = self._parse_bool(row.get("required"), "required", errors)
        sort_order = self._parse_int(row.get("sort_order"), "sort_order", errors)
        if errors:
            return None, errors

        template_label = template_name or f"template_id={template_id}"
        template_key = f"id:{template_id}" if template_id is not None else f"name-file:{template_name}|{template_file}"
        return (
            {
                "row_number": row_number,
                "template_id": template_id,
                "template_name": template_name,
                "template_file": template_file,
                "template_key": template_key,
                "template_label": template_label,
                "table_name": table_name,
                "table_name_cn": table_name_cn,
                "role": role_value,
                "relation_type": relation_type_value,
                "main_join_key": self._clean_text(row.get("main_join_key")),
                "table_join_key": self._clean_text(row.get("table_join_key")),
                "required": required,
                "sort_order": sort_order,
                "description": self._clean_text(row.get("description")),
            },
            [],
        )

    def _resolve_or_create_template(self, main_row: dict[str, Any], now: str) -> int:
        template_id = main_row.get("template_id")
        existing = self.template_repository.get_template_row(template_id) if template_id else None
        if existing is None:
            existing = self.template_repository.get_template_by_name_file(main_row["template_name"], main_row["template_file"])
        if existing:
            resolved_id = int(existing["id"])
            self.template_repository.update_template_relation_metadata(
                resolved_id,
                main_row["template_name"] or existing["template_name"],
                main_row["template_file"] or existing["template_file"],
                main_row["table_name"],
                now,
            )
            return resolved_id
        return self.template_repository.create_template_relation_template(
            template_name=main_row["template_name"],
            template_file=main_row["template_file"],
            main_table=main_row["table_name"],
            now=now,
            template_id=template_id,
        )

    def _preview_template_id(self, row: dict[str, Any]) -> int | None:
        template_id = row.get("template_id")
        if template_id and self.template_repository.get_template_row(template_id):
            return int(template_id)
        existing = self.template_repository.get_template_by_name_file(row["template_name"], row["template_file"])
        return int(existing["id"]) if existing else None

    def _template_file_is_known(self, template_file: str) -> bool:
        return self.template_repository.template_file_exists(template_file) or (self.settings.templates_dir / template_file).is_file()

    def _group_rows(self, rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["template_key"], []).append(row)
        return grouped

    def _build_preview(
        self,
        import_id: str,
        total_rows: int,
        items: list[TemplateRelationImportItem],
    ) -> TemplateRelationImportPreview:
        error_count = sum(1 for item in items if item.level == "error")
        warning_count = sum(1 for item in items if item.level == "warning")
        create_count = sum(1 for item in items if item.action == "create")
        update_count = sum(1 for item in items if item.action == "update")
        return TemplateRelationImportPreview(
            import_id=import_id,
            summary=TemplateRelationImportSummary(
                total_rows=total_rows,
                create_count=create_count,
                update_count=update_count,
                error_count=error_count,
                warning_count=warning_count,
            ),
            items=items,
            can_commit=error_count == 0,
        )

    def _save_preview(self, import_id: str, preview: TemplateRelationImportPreview, rows: list[dict[str, Any]]) -> None:
        self._preview_dir().mkdir(parents=True, exist_ok=True)
        payload = {"preview": preview.model_dump(mode="json"), "rows": rows}
        self._preview_path(import_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_preview(self, import_id: str) -> dict[str, Any]:
        if not import_id.startswith("tmp_"):
            raise AppError("BAD_REQUEST", "import_id 无效", 400)
        path = self._preview_path(import_id)
        if not path.exists():
            raise AppError("FILE_NOT_FOUND", "导入预览结果不存在或已过期", 404, {"import_id": import_id})
        return json.loads(path.read_text(encoding="utf-8"))

    def _preview_dir(self) -> Path:
        return self.settings.temp_dir / "template_relation_imports"

    def _preview_path(self, import_id: str) -> Path:
        return self._preview_dir() / f"{import_id}.json"

    def _parse_template_id(self, value: Any, errors: list[str]) -> int | None:
        if pd.isna(value) or self._clean_text(value) == "":
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            errors.append(f"template_id 必须是整数：{value}")
            return None
        if parsed <= 0:
            errors.append(f"template_id 必须大于 0：{value}")
            return None
        return parsed

    def _parse_bool(self, value: Any, column: str, errors: list[str]) -> bool:
        if pd.isna(value):
            return True
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        cleaned = str(value).strip().lower()
        if cleaned in TRUE_VALUES:
            return True
        if cleaned in FALSE_VALUES:
            return False
        errors.append(f"{column} 无法解析为 boolean：{value}")
        return True

    def _parse_int(self, value: Any, column: str, errors: list[str]) -> int:
        if pd.isna(value) or self._clean_text(value) == "":
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            errors.append(f"{column} 必须是整数：{value}")
            return 0

    def _clean_text(self, value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()
