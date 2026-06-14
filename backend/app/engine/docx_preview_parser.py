from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass(frozen=True)
class ParsedParagraph:
    text: str
    heading_level: int | None = None


@dataclass(frozen=True)
class ParsedTable:
    rows: list[list[str]]


ParsedDocxBlock = ParsedParagraph | ParsedTable


def parse_docx_for_preview(docx_path: Path) -> list[ParsedDocxBlock]:
    document = Document(str(docx_path))
    blocks: list[ParsedDocxBlock] = []

    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            paragraph = Paragraph(child, document)
            text = paragraph.text
            if text.strip():
                blocks.append(ParsedParagraph(text=text, heading_level=_heading_level(paragraph)))
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            rows = _parse_table_rows(table)
            if rows:
                blocks.append(ParsedTable(rows=rows))

    return blocks


def _parse_table_rows(table: Table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        cell_texts = [_cell_text(cell.text) for cell in row.cells]
        if any(text.strip() for text in cell_texts):
            rows.append(cell_texts)
    return rows


def _cell_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines()).strip()


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
