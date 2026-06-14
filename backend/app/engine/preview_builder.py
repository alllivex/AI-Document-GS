from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque
from uuid import uuid4

from app.engine.docx_preview_parser import ParsedDocxBlock, ParsedParagraph, ParsedTable, parse_docx_for_preview
from app.models.preview_models import (
    PreviewFile,
    PreviewHeadingBlock,
    PreviewParagraphBlock,
    PreviewRun,
    PreviewTableBlock,
    PreviewTableCell,
)
from app.models.trace_models import AITraceDetail, TraceItem
from app.models.trace_models import ConditionTraceDetail, LoopTraceDetail


TraceQueueByDisplayValue = dict[str, Deque[TraceItem]]


def build_preview_file(
    *,
    doc_id: str,
    task_id: str,
    output_file: str,
    primary_key_value: str,
    final_docx_path: Path,
    trace_items: list[TraceItem],
    condition_traces: list[ConditionTraceDetail] | None = None,
    loop_traces: list[LoopTraceDetail] | None = None,
    ai_traces: list[AITraceDetail] | None = None,
) -> PreviewFile:
    trace_queues = build_trace_queues(trace_items)
    blocks = build_preview_blocks(
        parse_docx_for_preview(final_docx_path),
        trace_queues,
        condition_traces=condition_traces or [],
        loop_traces=loop_traces or [],
        ai_traces=ai_traces or [],
    )

    return PreviewFile(
        doc_id=doc_id,
        task_id=task_id,
        title=output_file,
        output_file=output_file,
        primary_key_value=primary_key_value,
        blocks=blocks,
        created_at=datetime.now(timezone.utc),
    )


def build_preview_blocks(
    parsed_blocks: list[ParsedDocxBlock],
    trace_queues: TraceQueueByDisplayValue,
    condition_traces: list[ConditionTraceDetail] | None = None,
    loop_traces: list[LoopTraceDetail] | None = None,
    ai_traces: list[AITraceDetail] | None = None,
) -> list[PreviewHeadingBlock | PreviewParagraphBlock | PreviewTableBlock]:
    preview_blocks: list[PreviewHeadingBlock | PreviewParagraphBlock | PreviewTableBlock] = []
    remaining_conditions = list(condition_traces or [])
    remaining_loops = list(loop_traces or [])
    remaining_ai_traces = list(ai_traces or [])

    for parsed_block in parsed_blocks:
        if isinstance(parsed_block, ParsedParagraph):
            runs = split_text_with_trace(parsed_block.text, trace_queues)
            condition_trace = _match_condition_trace(parsed_block.text, remaining_conditions)
            if condition_trace is not None:
                _apply_condition_trace_to_runs(runs, condition_trace)
            ai_trace = _match_ai_trace(parsed_block.text, remaining_ai_traces)
            block_trace_id = ai_trace.trace_id if ai_trace else (condition_trace.trace_id if condition_trace else None)
            block_trace_kind = "ai" if ai_trace else ("condition" if condition_trace else None)
            if parsed_block.heading_level is not None:
                preview_blocks.append(
                    PreviewHeadingBlock(
                        block_id=_block_id("heading"),
                        level=parsed_block.heading_level,
                        text=parsed_block.text,
                    )
                )
            else:
                preview_blocks.append(
                    PreviewParagraphBlock(
                        block_id=_block_id("paragraph"),
                        block_trace_id=block_trace_id,
                        block_trace_kind=block_trace_kind,
                        runs=runs,
                    )
                )
        elif isinstance(parsed_block, ParsedTable):
            loop_trace = remaining_loops.pop(0) if remaining_loops else None
            preview_blocks.append(_build_table_block(parsed_block, trace_queues, loop_trace))

    return preview_blocks


def build_trace_queues(trace_items: list[TraceItem]) -> TraceQueueByDisplayValue:
    queues: TraceQueueByDisplayValue = {}
    for trace_item in trace_items:
        display_value = trace_item.display_value
        if not display_value:
            continue
        queues.setdefault(display_value, deque()).append(trace_item)
    return queues


def split_text_with_trace(text: str, trace_queues: TraceQueueByDisplayValue) -> list[PreviewRun]:
    runs: list[PreviewRun] = []
    position = 0

    while position < len(text):
        match = _find_next_trace_match(text, position, trace_queues)
        if match is None:
            _append_run(runs, text[position:])
            break

        start, display_value, trace_item = match
        if start > position:
            _append_run(runs, text[position:start])
        _append_run(runs, text[start : start + len(display_value)], trace_item.trace_id, "field")
        position = start + len(display_value)

    return runs


def _build_table_block(
    parsed_table: ParsedTable,
    trace_queues: TraceQueueByDisplayValue,
    loop_trace: LoopTraceDetail | None = None,
) -> PreviewTableBlock:
    raw_headers = parsed_table.rows[0] if parsed_table.rows else []
    raw_rows = parsed_table.rows[1:] if len(parsed_table.rows) > 1 else []

    return PreviewTableBlock(
        block_id=_block_id("table"),
        block_trace_id=loop_trace.trace_id if loop_trace else None,
        block_trace_kind="loop" if loop_trace else None,
        headers=[_build_table_cell(text, trace_queues) for text in raw_headers],
        rows=[
            [_build_table_cell(text, trace_queues) for text in row]
            for row in raw_rows
        ],
    )


def _build_table_cell(text: str, trace_queues: TraceQueueByDisplayValue) -> PreviewTableCell:
    match = _find_next_trace_match(text, 0, trace_queues)
    if match is None:
        return PreviewTableCell(text=text)

    _, _, trace_item = match
    return PreviewTableCell(text=text, trace_id=trace_item.trace_id, trace_kind="field")


def _find_next_trace_match(
    text: str,
    start_position: int,
    trace_queues: TraceQueueByDisplayValue,
) -> tuple[int, str, TraceItem] | None:
    best_match: tuple[int, str, TraceItem] | None = None

    for display_value, trace_queue in trace_queues.items():
        if not trace_queue:
            continue
        start = text.find(display_value, start_position)
        if start < 0:
            continue

        trace_item = trace_queue[0]
        if best_match is None:
            best_match = (start, display_value, trace_item)
            continue

        best_start, best_value, _ = best_match
        if start < best_start or (start == best_start and len(display_value) > len(best_value)):
            best_match = (start, display_value, trace_item)

    if best_match is None:
        return None

    _consume_trace_item(trace_queues, best_match[1])
    return best_match


def _consume_trace_item(trace_queues: TraceQueueByDisplayValue, display_value: str) -> None:
    trace_queue = trace_queues.get(display_value)
    if trace_queue and len(trace_queue) > 1:
        trace_queue.popleft()


def _append_run(
    runs: list[PreviewRun],
    text: str,
    trace_id: str | None = None,
    trace_kind: str | None = None,
) -> None:
    if not text:
        return
    if runs and runs[-1].trace_id == trace_id and runs[-1].trace_kind == trace_kind:
        runs[-1].text += text
        return
    runs.append(PreviewRun(text=text, trace_id=trace_id, trace_kind=trace_kind))


def _match_condition_trace(
    text: str,
    remaining_conditions: list[ConditionTraceDetail],
) -> ConditionTraceDetail | None:
    for index, condition_trace in enumerate(remaining_conditions):
        candidates = [condition_trace.actual_output_text, condition_trace.expected_output_text]
        if any(candidate and candidate in text for candidate in candidates):
            return remaining_conditions.pop(index)
    return None


def _match_ai_trace(
    text: str,
    remaining_ai_traces: list[AITraceDetail],
) -> AITraceDetail | None:
    normalized_text = _normalize_match_text(text)
    for index, ai_trace in enumerate(remaining_ai_traces):
        generated_text = _normalize_match_text(ai_trace.generated_text)
        if not generated_text:
            continue
        if generated_text in normalized_text or normalized_text in generated_text:
            return remaining_ai_traces.pop(index)
    return None


def _normalize_match_text(text: str) -> str:
    return "".join((text or "").split())


def _apply_condition_trace_to_runs(runs: list[PreviewRun], condition_trace: ConditionTraceDetail) -> None:
    target = condition_trace.actual_output_text or condition_trace.expected_output_text
    if not target:
        return
    for run in runs:
        if run.trace_id is None and run.text and target in run.text:
            run.trace_id = condition_trace.trace_id
            run.trace_kind = "condition"
            return
    for run in runs:
        if run.trace_id is None:
            run.trace_id = condition_trace.trace_id
            run.trace_kind = "condition"
            return


def _block_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
