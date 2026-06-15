from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

TWIPS_PER_PIXEL = 15
EMU_PER_PIXEL = 9525


@dataclass(frozen=True)
class ParsedRun:
    text: str
    style: dict[str, Any] | None = None


@dataclass(frozen=True)
class ParsedParagraph:
    text: str
    heading_level: int | None = None
    runs: list[ParsedRun] | None = None
    style: dict[str, Any] | None = None


@dataclass
class ParsedTableCell:
    text: str
    runs: list[ParsedRun]
    colspan: int = 1
    rowspan: int = 1
    style: dict[str, Any] | None = None
    width_px: float | None = None


@dataclass(frozen=True)
class ParsedTable:
    rows: list[list[ParsedTableCell]]
    style: dict[str, Any] | None = None
    width_px: float | None = None


ParsedDocxBlock = ParsedParagraph | ParsedTable


def parse_docx_for_preview(docx_path: Path) -> list[ParsedDocxBlock]:
    document = Document(str(docx_path))
    blocks: list[ParsedDocxBlock] = []

    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, document)
            text = paragraph.text
            if text.strip():
                blocks.append(
                    ParsedParagraph(
                        text=text,
                        heading_level=_heading_level(paragraph),
                        runs=_paragraph_runs(paragraph),
                        style=_paragraph_style(paragraph),
                    )
                )
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            rows = _parse_table_rows(table)
            if rows:
                blocks.append(ParsedTable(rows=rows, width_px=_table_width_px(table)))

    return blocks


def _parse_table_rows(table: Table) -> list[list[ParsedTableCell]]:
    rows: list[list[ParsedTableCell]] = []
    vertical_origins: dict[int, ParsedTableCell] = {}

    for row in table._tbl.tr_lst:
        parsed_row: list[ParsedTableCell] = []
        grid_column = 0

        for tc in row.tc_lst:
            grid_span = _grid_span(tc)
            vmerge_value = _vmerge_value(tc)

            if vmerge_value == "continue":
                origin = vertical_origins.get(grid_column)
                if origin is not None:
                    origin.rowspan += 1
                grid_column += grid_span
                continue

            for column in range(grid_column, grid_column + grid_span):
                vertical_origins.pop(column, None)

            cell = ParsedTableCell(
                text=_tc_text(tc),
                runs=_tc_runs(tc),
                colspan=grid_span,
                style=_tc_style(tc),
                width_px=_tc_width_px(tc),
            )
            if vmerge_value == "restart":
                for column in range(grid_column, grid_column + grid_span):
                    vertical_origins[column] = cell
            parsed_row.append(cell)
            grid_column += grid_span

        if any(cell.text.strip() for cell in parsed_row):
            rows.append(parsed_row)

    return rows


def _cell_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _tc_text(tc: Any) -> str:
    paragraphs = [Paragraph(p, None) for p in tc.iterchildren() if isinstance(p, CT_P)]
    return "\n".join(_cell_text(paragraph.text) for paragraph in paragraphs if paragraph.text.strip()).strip()


def _tc_runs(tc: Any) -> list[ParsedRun]:
    runs: list[ParsedRun] = []
    paragraphs = [Paragraph(p, None) for p in tc.iterchildren() if isinstance(p, CT_P)]
    for paragraph_index, paragraph in enumerate(paragraphs):
        if paragraph_index > 0 and runs:
            runs.append(ParsedRun(text="\n"))
        for run in _paragraph_runs(paragraph):
            runs.append(run)
    return runs


def _paragraph_runs(paragraph: Paragraph) -> list[ParsedRun]:
    runs: list[ParsedRun] = []
    for run in paragraph.runs:
        if run.text:
            runs.append(ParsedRun(text=run.text, style=_run_style(run)))
    if not runs and paragraph.text:
        runs.append(ParsedRun(text=paragraph.text))
    return runs


def _paragraph_style(paragraph: Paragraph) -> dict[str, Any] | None:
    style = _compact_style({"alignment": _alignment_name(paragraph.alignment)})
    return style


def _run_style(run: Run) -> dict[str, Any] | None:
    font = run.font
    color = None
    if font.color is not None and font.color.rgb is not None:
        color = str(font.color.rgb)
    font_size_pt = None
    if font.size is not None:
        font_size_pt = font.size.pt
    return _compact_style(
        {
            "bold": run.bold,
            "italic": run.italic,
            "underline": bool(run.underline) if run.underline is not None else None,
            "color": color,
            "font_size_pt": font_size_pt,
        }
    )


def _tc_style(tc: Any) -> dict[str, Any] | None:
    tc_pr = tc.tcPr
    shading = tc_pr.find(qn("w:shd")) if tc_pr is not None else None
    fill = shading.get(qn("w:fill")) if shading is not None else None
    return _compact_style({"background_color": fill if fill and fill != "auto" else None})


def _compact_style(values: dict[str, Any]) -> dict[str, Any] | None:
    compacted = {key: value for key, value in values.items() if value is not None}
    return compacted or None


def _alignment_name(alignment: WD_ALIGN_PARAGRAPH | None) -> str | None:
    if alignment is None:
        return None
    return {
        WD_ALIGN_PARAGRAPH.LEFT: "left",
        WD_ALIGN_PARAGRAPH.CENTER: "center",
        WD_ALIGN_PARAGRAPH.RIGHT: "right",
        WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    }.get(alignment)


def _grid_span(tc: Any) -> int:
    tc_pr = tc.tcPr
    grid_span = tc_pr.find(qn("w:gridSpan")) if tc_pr is not None else None
    if grid_span is None:
        return 1
    value = grid_span.get(qn("w:val"))
    return int(value) if value and value.isdigit() else 1


def _vmerge_value(tc: Any) -> str | None:
    tc_pr = tc.tcPr
    vmerge = tc_pr.find(qn("w:vMerge")) if tc_pr is not None else None
    if vmerge is None:
        return None
    value = vmerge.get(qn("w:val"))
    return "restart" if value == "restart" else "continue"


def _tc_width_px(tc: Any) -> float | None:
    tc_pr = tc.tcPr
    tc_width = tc_pr.find(qn("w:tcW")) if tc_pr is not None else None
    return _word_width_px(tc_width)


def _table_width_px(table: Table) -> float | None:
    tbl_pr = table._tbl.tblPr
    tbl_width = tbl_pr.find(qn("w:tblW")) if tbl_pr is not None else None
    return _word_width_px(tbl_width)


def _word_width_px(width_element: Any) -> float | None:
    if width_element is None:
        return None
    value = width_element.get(qn("w:w"))
    width_type = width_element.get(qn("w:type"))
    if not value or not value.lstrip("-").isdigit():
        return None
    width = int(value)
    if width <= 0 or width_type == "pct":
        return None
    if width_type == "dxa" or width_type is None:
        return round(width / TWIPS_PER_PIXEL, 2)
    return round(width / EMU_PER_PIXEL, 2)


def _heading_level(paragraph: Paragraph) -> int | None:
    style_name = _paragraph_style_name(paragraph)
    match = re.search(r"(?:Heading|标题)\s*([1-6])", style_name, flags=re.IGNORECASE)
    if match is None:
        return None
    return int(match.group(1))


def _paragraph_style_name(paragraph: Paragraph) -> str:
    try:
        return paragraph.style.name or ""
    except (AttributeError, KeyError):
        return ""
