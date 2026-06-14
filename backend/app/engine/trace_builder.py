from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.engine.preview_builder import build_preview_file
from app.engine.docx_preview_parser import ParsedParagraph, ParsedTable, parse_docx_for_preview
from app.engine.template_parser import ConditionBlock, LoopBlock, extract_template_trace_blocks
from app.engine.value_formatter import unwrap_raw_value
from app.models.file_models import SourceFileInfo
from app.models.trace_models import (
    AIBlockTrace,
    AIInputVariable,
    AITraceDetail,
    ConditionTraceDetail,
    KnowledgeReference,
    LoopTraceDetail,
    SourceRecordField,
    SourceRecordView,
    TraceFile,
    TraceItem,
    TraceStatistics,
)


AI_KB_PATTERN = re.compile(r"{kb:([A-Za-z_][A-Za-z0-9_-]*)}")
AI_VARIABLE_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")


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
    template_path: Path | None = None


class BuildTracePreviewResult(BaseModel):
    trace_file_path: Path
    preview_file_path: Path
    trace_count: int
    ai_block_count: int


def build_trace_and_preview(input_data: BuildTracePreviewInput) -> BuildTracePreviewResult:
    trace_items = flatten_trace_map(input_data.trace_map)
    condition_traces, loop_traces = build_block_trace_details(input_data, trace_items)
    ai_traces = build_ai_trace_details(input_data, trace_items)
    trace_file = build_trace_file(input_data, trace_items, condition_traces, loop_traces, ai_traces)

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
        condition_traces=condition_traces,
        loop_traces=loop_traces,
        ai_traces=ai_traces,
    )
    _write_json(preview_file_path, preview_file)

    return BuildTracePreviewResult(
        trace_file_path=trace_file_path,
        preview_file_path=preview_file_path,
        trace_count=len(trace_items),
        ai_block_count=len(input_data.ai_blocks),
    )


def build_trace_file(
    input_data: BuildTracePreviewInput,
    trace_items: list[TraceItem],
    condition_traces: list[ConditionTraceDetail] | None = None,
    loop_traces: list[LoopTraceDetail] | None = None,
    ai_traces: list[AITraceDetail] | None = None,
) -> TraceFile:
    current_condition_traces = condition_traces or []
    current_loop_traces = loop_traces or []
    current_ai_traces = ai_traces or []
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
        condition_traces=current_condition_traces,
        loop_traces=current_loop_traces,
        ai_traces=current_ai_traces,
        ai_blocks=input_data.ai_blocks,
        statistics=TraceStatistics(
            trace_item_count=len(trace_items),
            ai_block_count=len(input_data.ai_blocks),
            source_file_count=len({item.source_file_path for item in trace_items}),
            table_count=len({item.table_name for item in trace_items}),
        ),
    )


def build_ai_trace_details(
    input_data: BuildTracePreviewInput,
    trace_items: list[TraceItem],
) -> list[AITraceDetail]:
    trace_item_by_var_path = {item.var_path: item for item in trace_items}
    return [
        AITraceDetail(
            trace_id=_make_ai_trace_id(input_data.doc_id, block.block_id),
            task_id=input_data.task_id,
            doc_id=input_data.doc_id,
            primary_key_value=input_data.primary_key_value,
            block_id=block.block_id,
            marker=block.marker,
            status=_ai_trace_status(block.status),
            original_block_text=block.original_block_text,
            prompt_template=block.prompt_template,
            prompt_rendered=block.prompt_rendered,
            model=block.model,
            temperature=0.2 if block.model else None,
            started_at=block.started_at,
            completed_at=block.completed_at,
            input_variables=_build_ai_input_variables(block, trace_item_by_var_path),
            knowledge_refs=_build_knowledge_refs(block),
            generated_text=_ai_trace_generated_text(block),
            error_message=block.error_message,
        )
        for block in input_data.ai_blocks
    ]


def flatten_trace_map(trace_map: dict[str, list[TraceItem]]) -> list[TraceItem]:
    trace_items: list[TraceItem] = []
    for items in trace_map.values():
        trace_items.extend(items)
    return trace_items


def build_block_trace_details(
    input_data: BuildTracePreviewInput,
    trace_items: list[TraceItem],
) -> tuple[list[ConditionTraceDetail], list[LoopTraceDetail]]:
    if input_data.template_path is None or not input_data.template_path.exists():
        return [], []

    template_blocks = extract_template_trace_blocks(input_data.template_path)
    parsed_blocks = parse_docx_for_preview(input_data.final_docx_path)
    condition_traces = [
        _build_condition_trace(input_data, block, trace_items, parsed_blocks)
        for block in template_blocks.conditions
    ]
    loop_traces = [
        _build_loop_trace(input_data, block, trace_items)
        for block in template_blocks.loops
    ]
    return condition_traces, loop_traces


def build_source_record_view(
    trace_items: list[TraceItem],
    target_item: TraceItem,
    highlighted_fields: set[str] | None = None,
    highlight_reason: str = "none",
) -> SourceRecordView:
    highlighted = highlighted_fields or {target_item.field_name}
    record_items = [
        item
        for item in trace_items
        if item.table_name == target_item.table_name
        and item.row_index == target_item.row_index
        and item.occurrence_index == target_item.occurrence_index
    ]
    record_items.sort(key=lambda item: item.column_index if item.column_index is not None else 9999)
    return SourceRecordView(
        table_name=target_item.table_name,
        table_name_cn=target_item.table_name_cn,
        source_file=target_item.source_file,
        row_index=target_item.row_index,
        excel_row_number=target_item.excel_row_number,
        relation_type=target_item.source_relation_type,
        fields=[
            SourceRecordField(
                field_name=item.field_name,
                field_name_cn=item.field_name_cn,
                raw_value=item.raw_value,
                display_value=item.display_value,
                value_type=getattr(item.value_type, "value", item.value_type),
                excel_column_letter=item.excel_column_letter,
                is_highlighted=item.field_name in highlighted or item.var_path in highlighted,
                highlight_reason=highlight_reason if item.field_name in highlighted or item.var_path in highlighted else "none",
            )
            for item in record_items
        ],
    )


def _build_condition_trace(
    input_data: BuildTracePreviewInput,
    block: ConditionBlock,
    trace_items: list[TraceItem],
    parsed_blocks: list[Any],
) -> ConditionTraceDetail:
    evaluated_result = _evaluate_condition(block.expression, trace_items)
    selected_branch = "if" if evaluated_result else "else"
    expected_output = block.if_text if evaluated_result else (block.else_text or "")
    actual_output = _find_actual_condition_output(block, parsed_blocks)
    used_item_by_record: dict[tuple[str, int, int], TraceItem] = {}
    used_var_set = set(block.used_variables)

    for item in trace_items:
        if item.var_path in used_var_set:
            used_item_by_record.setdefault((item.table_name, item.row_index, item.occurrence_index), item)

    source_records = [
        build_source_record_view(
            trace_items,
            item,
            highlighted_fields=used_var_set,
            highlight_reason="used_in_condition",
        )
        for item in used_item_by_record.values()
    ]

    return ConditionTraceDetail(
        trace_id=f"trace_condition_{input_data.doc_id}_{block.block_id}",
        task_id=input_data.task_id,
        doc_id=input_data.doc_id,
        primary_key_value=input_data.primary_key_value,
        expression=block.expression,
        used_variables=block.used_variables,
        evaluated_result=evaluated_result,
        selected_branch=selected_branch,
        expected_output_text=expected_output,
        actual_output_text=actual_output,
        is_consistent=bool(expected_output and expected_output in actual_output),
        source_records=source_records,
    )


def _build_loop_trace(
    input_data: BuildTracePreviewInput,
    block: LoopBlock,
    trace_items: list[TraceItem],
) -> LoopTraceDetail:
    table_items = [item for item in trace_items if item.table_name == block.table_name]
    first_item = table_items[0] if table_items else None
    records: dict[tuple[int, int], TraceItem] = {}
    for item in table_items:
        records.setdefault((item.row_index, item.occurrence_index), item)

    return LoopTraceDetail(
        trace_id=f"trace_loop_{input_data.doc_id}_{block.block_id}",
        task_id=input_data.task_id,
        doc_id=input_data.doc_id,
        primary_key_value=input_data.primary_key_value,
        table_name=block.table_name,
        table_name_cn=first_item.table_name_cn if first_item else "",
        loop_alias=block.loop_alias,
        used_fields=block.used_fields,
        matched_row_count=len(records),
        source_records=[
            build_source_record_view(
                trace_items,
                item,
                highlighted_fields=set(block.used_fields),
                highlight_reason="used_in_loop",
            )
            for item in records.values()
        ],
    )


def _build_ai_input_variables(
    block: AIBlockTrace,
    trace_item_by_var_path: dict[str, TraceItem],
) -> list[AIInputVariable]:
    variable_paths = _extract_ai_variable_paths(" ".join([block.prompt_template, block.prompt_rendered]))
    input_variables: list[AIInputVariable] = []
    for var_path in variable_paths:
        table_name, field_name = var_path.split(".", 1)
        trace_item = trace_item_by_var_path.get(var_path)
        input_variables.append(
            AIInputVariable(
                original_var_path=trace_item.original_var_path if trace_item else var_path,
                canonical_var_path=trace_item.canonical_var_path if trace_item else var_path,
                var_path=var_path,
                table_name=table_name,
                table_name_cn=trace_item.table_name_cn if trace_item else "",
                field_name=field_name,
                field_name_cn=trace_item.field_name_cn if trace_item else "",
                raw_value=trace_item.raw_value if trace_item else None,
                display_value=trace_item.display_value if trace_item else "",
                trace_id=trace_item.trace_id if trace_item else None,
                source_file=trace_item.source_file if trace_item else "",
                excel_row_number=trace_item.excel_row_number if trace_item else None,
                excel_column_letter=trace_item.excel_column_letter if trace_item else None,
            )
        )
    return input_variables


def _build_knowledge_refs(block: AIBlockTrace) -> list[KnowledgeReference]:
    names = []
    seen: set[str] = set()
    for text in (block.prompt_template, block.prompt_rendered):
        for match in AI_KB_PATTERN.finditer(text):
            kb_name = match.group(1)
            if kb_name not in seen:
                names.append(kb_name)
                seen.add(kb_name)
    return [KnowledgeReference(kb_name=name, retrieval_enabled=False) for name in names]


def _extract_ai_variable_paths(text: str) -> list[str]:
    variables: list[str] = []
    seen: set[str] = set()
    for root_name, field_name in AI_VARIABLE_PATTERN.findall(text):
        var_path = f"{root_name}.{field_name}"
        if var_path in seen:
            continue
        variables.append(var_path)
        seen.add(var_path)
    return variables


def _ai_trace_status(status: Any) -> str:
    value = getattr(status, "value", status)
    if value == "success":
        return "success"
    if value == "failed":
        return "failed"
    return "skipped"


def _ai_trace_generated_text(block: AIBlockTrace) -> str:
    if getattr(block.status, "value", block.status) == "success":
        return block.generated_text
    if getattr(block.status, "value", block.status) == "failed":
        return ""
    return block.original_block_text.replace(block.marker, "").strip()


def _evaluate_condition(expression: str, trace_items: list[TraceItem]) -> bool:
    class Namespace:
        pass

    context: dict[str, Any] = {}
    for item in trace_items:
        table_namespace = context.setdefault(item.table_name, Namespace())
        setattr(table_namespace, item.field_name, item.raw_value)
    try:
        return bool(eval(expression, {"__builtins__": {}}, context))
    except Exception:
        return False


def _find_actual_condition_output(block: ConditionBlock, parsed_blocks: list[Any]) -> str:
    candidates = [value for value in (block.if_text, block.else_text) if value]
    for parsed_block in parsed_blocks:
        if isinstance(parsed_block, ParsedParagraph):
            for candidate in candidates:
                if candidate and candidate in parsed_block.text:
                    return parsed_block.text
    return ""


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


def _make_ai_trace_id(doc_id: str, block_id: str) -> str:
    return f"trace_ai_{doc_id}_{block_id}"


def _write_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = model.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
