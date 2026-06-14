from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from pathlib import Path
import re
import zipfile

from app.engine.template_canonicalizer import (
    MissingTemplateVariable,
    TemplateVariableResolver,
    canonicalize_jinja_text,
)
from app.models.template_models import FieldDefinition

JINJA_TAG_PATTERN = re.compile(r"({[{%#].*?[}%]})", re.DOTALL)
IDENT_PATTERN = r"[^\W\d]\w*"
DOTTED_NAME_PATTERN = re.compile(
    rf"(?<![\w])({IDENT_PATTERN})\s*\.\s*({IDENT_PATTERN})(?![\w])",
    re.UNICODE,
)
FOR_PATTERN = re.compile(
    rf"{{%\s*(?:tr\s+)?for\s+({IDENT_PATTERN})\s+in\s+({IDENT_PATTERN})",
    re.DOTALL | re.UNICODE,
)
IGNORED_ROOT_NAMES = {"loop", "cycler", "namespace", "super", "true", "false", "none"}
IF_BLOCK_PATTERN = re.compile(
    r"{%\s*if\s+(.*?)\s*%}(.*?)(?:{%\s*else\s*%}(.*?))?{%\s*endif\s*%}",
    re.DOTALL,
)
LOOP_BLOCK_PATTERN = re.compile(
    rf"{{%\s*tr\s+for\s+({IDENT_PATTERN})\s+in\s+({IDENT_PATTERN})\s*%}}"
    r"(.*?)"
    r"{%\s*tr\s+endfor\s*%}",
    re.DOTALL | re.UNICODE,
)


@dataclass(frozen=True)
class TemplateFieldReference:
    variable_path: str
    table_name: str
    field_name: str
    original_variable_path: str | None = None


@dataclass(frozen=True)
class ConditionBlock:
    block_id: str
    expression: str
    used_variables: list[str]
    if_text: str
    else_text: str | None = None


@dataclass(frozen=True)
class LoopBlock:
    block_id: str
    table_name: str
    loop_alias: str
    used_fields: list[str]


@dataclass(frozen=True)
class TemplateTraceBlocks:
    conditions: list[ConditionBlock]
    loops: list[LoopBlock]


def extract_template_field_references(template_path: Path) -> list[TemplateFieldReference]:
    text = _read_docx_template_text(template_path)
    return extract_template_field_references_from_text(text)


def extract_template_field_references_from_text(text: str) -> list[TemplateFieldReference]:
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
                original_variable_path=variable_path,
            )

    return list(references.values())


def extract_canonical_template_field_references(
    template_path: Path,
    fields: list[FieldDefinition],
) -> tuple[list[TemplateFieldReference], dict[str, str]]:
    references, original_by_canonical, _missing = analyze_template_variables(template_path, fields)
    return references, original_by_canonical


def analyze_template_variables(
    template_path: Path,
    fields: list[FieldDefinition],
) -> tuple[list[TemplateFieldReference], dict[str, str], list[MissingTemplateVariable]]:
    text = _read_docx_template_text(template_path)
    canonicalized = canonicalize_jinja_text(text, TemplateVariableResolver(fields))
    references = extract_template_field_references_from_text(canonicalized.text)
    for reference in references:
        object.__setattr__(
            reference,
            "original_variable_path",
            canonicalized.original_var_paths_by_canonical.get(reference.variable_path, reference.variable_path),
        )
    return references, canonicalized.original_var_paths_by_canonical, canonicalized.missing_variables


def extract_jinja_variables_from_docx(template_path: Path) -> set[str]:
    return {reference.variable_path for reference in extract_template_field_references(template_path)}


def extract_template_trace_blocks(template_path: Path) -> TemplateTraceBlocks:
    text = _read_docx_template_text(template_path)
    return TemplateTraceBlocks(
        conditions=_extract_condition_blocks(text),
        loops=_extract_loop_blocks(text),
    )


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


def _extract_condition_blocks(text: str) -> list[ConditionBlock]:
    blocks: list[ConditionBlock] = []
    for index, match in enumerate(IF_BLOCK_PATTERN.finditer(text)):
        expression = match.group(1).strip()
        blocks.append(
            ConditionBlock(
                block_id=f"condition_{index}",
                expression=expression,
                used_variables=_extract_variable_paths(expression),
                if_text=_clean_block_text(match.group(2)),
                else_text=_clean_block_text(match.group(3)) if match.group(3) is not None else None,
            )
        )
    return blocks


def _extract_loop_blocks(text: str) -> list[LoopBlock]:
    blocks: list[LoopBlock] = []
    for index, match in enumerate(LOOP_BLOCK_PATTERN.finditer(text)):
        loop_alias = match.group(1)
        table_name = match.group(2)
        body = match.group(3)
        used_fields = sorted(
            {
                f"{table_name}.{field_name}"
                for root_name, field_name in DOTTED_NAME_PATTERN.findall(body)
                if root_name == loop_alias
            }
        )
        blocks.append(
            LoopBlock(
                block_id=f"loop_{index}",
                table_name=table_name,
                loop_alias=loop_alias,
                used_fields=used_fields,
            )
        )
    return blocks


def _extract_variable_paths(text: str) -> list[str]:
    return sorted(
        {
            f"{root_name}.{field_name}"
            for root_name, field_name in DOTTED_NAME_PATTERN.findall(text)
            if root_name.lower() not in IGNORED_ROOT_NAMES
        }
    )


def _clean_block_text(text: str | None) -> str:
    if not text:
        return ""
    without_tags = JINJA_TAG_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", without_tags).strip()


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
