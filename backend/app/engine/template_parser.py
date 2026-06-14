from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import zipfile

JINJA_TAG_PATTERN = re.compile(r"({[{%#].*?[}%]})", re.DOTALL)
DOTTED_NAME_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
FOR_PATTERN = re.compile(
    r"{%\s*(?:tr\s+)?for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.DOTALL,
)
IGNORED_ROOT_NAMES = {"loop", "cycler", "namespace", "super", "true", "false", "none"}


@dataclass(frozen=True)
class TemplateFieldReference:
    variable_path: str
    table_name: str
    field_name: str


def extract_template_field_references(template_path: Path) -> list[TemplateFieldReference]:
    text = _read_docx_template_text(template_path)
    tags = JINJA_TAG_PATTERN.findall(text)
    loop_table_by_variable = _extract_loop_table_by_variable(tags)
    references: dict[tuple[str, str], TemplateFieldReference] = {}

    for tag in tags:
        for root_name, field_name in DOTTED_NAME_PATTERN.findall(tag):
            if root_name.lower() in IGNORED_ROOT_NAMES:
                continue

            table_name = loop_table_by_variable.get(root_name, root_name)
            variable_path = f"{table_name}.{field_name}"
            references[(table_name, field_name)] = TemplateFieldReference(
                variable_path=variable_path,
                table_name=table_name,
                field_name=field_name,
            )

    return list(references.values())


def extract_jinja_variables_from_docx(template_path: Path) -> set[str]:
    return {reference.variable_path for reference in extract_template_field_references(template_path)}


def split_var_path(var_path: str) -> tuple[str, str]:
    parts = var_path.split(".")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"template variable must use table.field format: {var_path}")
    return parts[0], parts[1]


def _extract_loop_table_by_variable(tags: list[str]) -> dict[str, str]:
    loop_table_by_variable: dict[str, str] = {}
    for tag in tags:
        match = FOR_PATTERN.search(tag)
        if match:
            loop_table_by_variable[match.group(1)] = match.group(2)
    return loop_table_by_variable


def _read_docx_template_text(template_path: Path) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"template file not found: {template_path}")

    fragments: list[str] = []
    with zipfile.ZipFile(template_path) as archive:
        xml_names = [
            name
            for name in archive.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        ]
        for name in sorted(xml_names):
            xml_text = archive.read(name).decode("utf-8", errors="ignore")
            fragments.append(_strip_xml_tags(xml_text))

    return "\n".join(fragments)


def _strip_xml_tags(xml_text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", xml_text))
