from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.engine.preview_builder import build_preview_file
from app.models.file_models import SourceFileInfo
from app.models.trace_models import AIBlockTrace, TraceFile, TraceItem, TraceStatistics


class BuildTracePreviewInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str
    doc_id: str
    template_id: int
    template_name: str
    template_file: str
    output_file: str
    output_path: Path
    main_table: str
    main_table_cn: str = ""
    primary_key_field: str
    primary_key_value: str
    trace_map: dict[str, list[TraceItem]]
    ai_blocks: list[AIBlockTrace] = []
    final_docx_path: Path


class BuildTracePreviewResult(BaseModel):
    trace_file_path: Path
    preview_file_path: Path
    trace_count: int
    ai_block_count: int


def build_trace_and_preview(input_data: BuildTracePreviewInput) -> BuildTracePreviewResult:
    trace_items = flatten_trace_map(input_data.trace_map)
    trace_file = build_trace_file(input_data, trace_items)

    trace_file_path = _sidecar_path(input_data.output_path, ".trace.json")
    preview_file_path = _sidecar_path(input_data.output_path, ".preview.json")

    _write_json(trace_file_path, trace_file)

    preview_file = build_preview_file(
        doc_id=input_data.doc_id,
        task_id=input_data.task_id,
        output_file=input_data.output_file,
        primary_key_value=input_data.primary_key_value,
        final_docx_path=input_data.final_docx_path,
        trace_items=trace_items,
    )
    _write_json(preview_file_path, preview_file)

    return BuildTracePreviewResult(
        trace_file_path=trace_file_path,
        preview_file_path=preview_file_path,
        trace_count=len(trace_items),
        ai_block_count=len(input_data.ai_blocks),
    )


def build_trace_file(input_data: BuildTracePreviewInput, trace_items: list[TraceItem]) -> TraceFile:
    return TraceFile(
        doc_id=input_data.doc_id,
        task_id=input_data.task_id,
        template_id=input_data.template_id,
        template_name=input_data.template_name,
        template_file=input_data.template_file,
        output_file=input_data.output_file,
        output_path=str(input_data.output_path),
        main_table=input_data.main_table,
        main_table_cn=input_data.main_table_cn,
        primary_key_field=input_data.primary_key_field,
        primary_key_value=input_data.primary_key_value,
        generated_at=datetime.now(timezone.utc),
        source_files=_build_source_files(trace_items),
        trace_items=trace_items,
        ai_blocks=input_data.ai_blocks,
        statistics=TraceStatistics(
            trace_item_count=len(trace_items),
            ai_block_count=len(input_data.ai_blocks),
            source_file_count=len({item.source_file_path for item in trace_items}),
            table_count=len({item.table_name for item in trace_items}),
        ),
    )


def flatten_trace_map(trace_map: dict[str, list[TraceItem]]) -> list[TraceItem]:
    trace_items: list[TraceItem] = []
    for items in trace_map.values():
        trace_items.extend(items)
    return trace_items


def _build_source_files(trace_items: list[TraceItem]) -> list[SourceFileInfo]:
    source_files: dict[tuple[str, str], SourceFileInfo] = {}

    for item in trace_items:
        key = (item.table_name, item.source_file_path)
        if key in source_files:
            continue
        source_files[key] = SourceFileInfo(
            table_name=item.table_name,
            table_name_cn=item.table_name_cn,
            filename=item.source_file,
            path=item.source_file_path,
            row_count=0,
            column_count=0,
        )

    return list(source_files.values())


def _sidecar_path(output_path: Path, suffix: str) -> Path:
    return Path(output_path).with_suffix(suffix)


def _write_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = model.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
