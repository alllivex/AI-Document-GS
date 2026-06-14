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
from app.models.trace_models import TraceItem


TraceQueueByDisplayValue = dict[str, Deque[TraceItem]]


def build_preview_file(
    *,
    doc_id: str,
    task_id: str,
    output_file: str,
    primary_key_value: str,
    final_docx_path: Path,
    trace_items: list[TraceItem],
) -> PreviewFile:
    trace_queues = build_trace_queues(trace_items)
    blocks = build_preview_blocks(parse_docx_for_preview(final_docx_path), trace_queues)

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
) -> list[PreviewHeadingBlock | PreviewParagraphBlock | PreviewTableBlock]:
    preview_blocks: list[PreviewHeadingBlock | PreviewParagraphBlock | PreviewTableBlock] = []

    for parsed_block in parsed_blocks:
        if isinstance(parsed_block, ParsedParagraph):
            runs = split_text_with_trace(parsed_block.text, trace_queues)
            if parsed_block.heading_level is not None:
                preview_blocks.append(
                    PreviewHeadingBlock(
                        block_id=_block_id("heading"),
                        level=parsed_block.heading_level,
                        text=parsed_block.text,
                    )
                )
            else:
                preview_blocks.append(PreviewParagraphBlock(block_id=_block_id("paragraph"), runs=runs))
        elif isinstance(parsed_block, ParsedTable):
            preview_blocks.append(_build_table_block(parsed_block, trace_queues))

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
        _append_run(runs, text[start : start + len(display_value)], trace_item.trace_id)
        position = start + len(display_value)

    return runs


def _build_table_block(parsed_table: ParsedTable, trace_queues: TraceQueueByDisplayValue) -> PreviewTableBlock:
    raw_headers = parsed_table.rows[0] if parsed_table.rows else []
    raw_rows = parsed_table.rows[1:] if len(parsed_table.rows) > 1 else []

    return PreviewTableBlock(
        block_id=_block_id("table"),
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
    return PreviewTableCell(text=text, trace_id=trace_item.trace_id)


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
    if trace_queue:
        trace_queue.popleft()


def _append_run(runs: list[PreviewRun], text: str, trace_id: str | None = None) -> None:
    if not text:
        return
    if runs and runs[-1].trace_id == trace_id:
        runs[-1].text += text
        return
    runs.append(PreviewRun(text=text, trace_id=trace_id))


def _block_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
