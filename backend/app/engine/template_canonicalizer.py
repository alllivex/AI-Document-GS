from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
import re
import zipfile

from app.models.template_models import FieldDefinition

IDENT_PATTERN = r"[^\W\d]\w*"
JINJA_TAG_PATTERN = re.compile(r"({[{%#].*?[}%]})", re.DOTALL)
DOTTED_NAME_PATTERN = re.compile(
    rf"(?<![\w])(?P<root>{IDENT_PATTERN})\s*\.\s*(?P<field>{IDENT_PATTERN})(?![\w])",
    re.UNICODE,
)
FOR_PATTERN = re.compile(
    rf"{{%\s*(?:tr\s+)?for\s+(?P<alias>{IDENT_PATTERN})\s+in\s+(?P<table>{IDENT_PATTERN})",
    re.DOTALL | re.UNICODE,
)
IGNORED_ROOT_NAMES = {"loop", "cycler", "namespace", "super", "true", "false", "none"}


@dataclass(frozen=True)
class MissingTemplateVariable:
    original_var_path: str
    table_name: str
    field_name: str
    reason: str


@dataclass(frozen=True)
class CanonicalTemplateResult:
    output_path: Path
    original_var_paths_by_canonical: dict[str, str]
    missing_variables: list[MissingTemplateVariable] = field(default_factory=list)


@dataclass(frozen=True)
class CanonicalizeTextResult:
    text: str
    original_var_paths_by_canonical: dict[str, str]
    missing_variables: list[MissingTemplateVariable]


class TemplateVariableResolver:
    def __init__(self, fields: list[FieldDefinition]) -> None:
        self.table_en_to_cn: dict[str, str] = {}
        self.table_cn_to_en: dict[str, str] = {}
        self.fields_by_table: dict[str, set[str]] = {}
        self.field_cn_to_en_by_table: dict[str, dict[str, str]] = {}

        for field in fields:
            self.fields_by_table.setdefault(field.table_name, set()).add(field.field_name)
            if field.table_name_cn:
                self.table_en_to_cn[field.table_name] = field.table_name_cn
                self.table_cn_to_en[field.table_name_cn] = field.table_name
            if field.field_name_cn:
                self.field_cn_to_en_by_table.setdefault(field.table_name, {})[field.field_name_cn] = field.field_name

    def resolve_table(self, table_name: str) -> str | None:
        if table_name in self.fields_by_table:
            return table_name
        return self.table_cn_to_en.get(table_name)

    def resolve_field(self, table_name: str, field_name: str) -> str | None:
        fields = self.fields_by_table.get(table_name, set())
        if field_name in fields:
            return field_name
        return self.field_cn_to_en_by_table.get(table_name, {}).get(field_name)


def canonicalize_docx_template(
    template_path: Path,
    output_path: Path,
    fields: list[FieldDefinition],
) -> CanonicalTemplateResult:
    resolver = TemplateVariableResolver(fields)
    original_by_canonical: dict[str, str] = {}
    missing_variables: list[MissingTemplateVariable] = []
    loop_alias_table_names: dict[str, str] = {}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(template_path, "r") as source, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    target.writestr(item, data)
                    continue

                canonicalized = canonicalize_jinja_text(
                    text,
                    resolver,
                    loop_alias_table_names=loop_alias_table_names,
                )
                original_by_canonical.update(
                    {
                        canonical: original_by_canonical.get(canonical, original)
                        for canonical, original in canonicalized.original_var_paths_by_canonical.items()
                    }
                )
                missing_variables.extend(canonicalized.missing_variables)
                canonical_text = _replace_split_jinja_tags(
                    canonicalized.text,
                    resolver,
                    loop_alias_table_names,
                    original_by_canonical,
                    missing_variables,
                )
                target.writestr(item, canonical_text.encode("utf-8"))
            else:
                target.writestr(item, data)

    return CanonicalTemplateResult(
        output_path=output_path,
        original_var_paths_by_canonical=original_by_canonical,
        missing_variables=_unique_missing_variables(missing_variables),
    )


def canonicalize_jinja_text(
    text: str,
    resolver: TemplateVariableResolver,
    loop_alias_table_names: dict[str, str] | None = None,
) -> CanonicalizeTextResult:
    alias_table_names = loop_alias_table_names if loop_alias_table_names is not None else {}
    original_by_canonical: dict[str, str] = {}
    missing_variables: list[MissingTemplateVariable] = []

    def replace_tag(match: re.Match[str]) -> str:
        tag = match.group(0)
        tag = _canonicalize_loop_table(tag, resolver, alias_table_names, missing_variables)

        def replace_variable(variable_match: re.Match[str]) -> str:
            root_name = variable_match.group("root")
            field_name = variable_match.group("field")
            if root_name.lower() in IGNORED_ROOT_NAMES:
                return variable_match.group(0)

            original_var_path = f"{root_name}.{field_name}"
            if root_name in alias_table_names:
                canonical_table = alias_table_names[root_name]
                canonical_field = resolver.resolve_field(canonical_table, field_name)
                if canonical_field is None:
                    missing_variables.append(
                        MissingTemplateVariable(
                            original_var_path=original_var_path,
                            table_name=canonical_table,
                            field_name=field_name,
                            reason="field_not_found",
                        )
                    )
                    return variable_match.group(0)
                canonical_path = f"{canonical_table}.{canonical_field}"
                original_by_canonical.setdefault(canonical_path, original_var_path)
                return f"{root_name}.{canonical_field}"

            canonical_table = resolver.resolve_table(root_name)
            if canonical_table is None:
                missing_variables.append(
                    MissingTemplateVariable(
                        original_var_path=original_var_path,
                        table_name=root_name,
                        field_name=field_name,
                        reason="table_not_found",
                    )
                )
                return variable_match.group(0)

            canonical_field = resolver.resolve_field(canonical_table, field_name)
            if canonical_field is None:
                missing_variables.append(
                    MissingTemplateVariable(
                        original_var_path=original_var_path,
                        table_name=canonical_table,
                        field_name=field_name,
                        reason="field_not_found",
                    )
                )
                return variable_match.group(0)

            canonical_path = f"{canonical_table}.{canonical_field}"
            original_by_canonical.setdefault(canonical_path, original_var_path)
            return canonical_path

        return DOTTED_NAME_PATTERN.sub(replace_variable, tag)

    return CanonicalizeTextResult(
        text=JINJA_TAG_PATTERN.sub(replace_tag, text),
        original_var_paths_by_canonical=original_by_canonical,
        missing_variables=_unique_missing_variables(missing_variables),
    )


def _canonicalize_loop_table(
    tag: str,
    resolver: TemplateVariableResolver,
    alias_table_names: dict[str, str],
    missing_variables: list[MissingTemplateVariable],
) -> str:
    match = FOR_PATTERN.search(tag)
    if match is None:
        return tag

    alias = match.group("alias")
    table_name = match.group("table")
    canonical_table = resolver.resolve_table(table_name)
    if canonical_table is None:
        missing_variables.append(
            MissingTemplateVariable(
                original_var_path=table_name,
                table_name=table_name,
                field_name="",
                reason="table_not_found",
            )
        )
        return tag

    alias_table_names[alias] = canonical_table
    return f"{tag[:match.start('table')]}{canonical_table}{tag[match.end('table'):]}"


def _replace_split_jinja_tags(
    xml_text: str,
    resolver: TemplateVariableResolver,
    loop_alias_table_names: dict[str, str],
    original_by_canonical: dict[str, str],
    missing_variables: list[MissingTemplateVariable],
) -> str:
    stripped_text = unescape(re.sub(r"<[^>]+>", "", xml_text))
    original_tags = JINJA_TAG_PATTERN.findall(stripped_text)
    if not original_tags:
        return xml_text

    canonicalized = canonicalize_jinja_text(
        stripped_text,
        resolver,
        loop_alias_table_names=loop_alias_table_names,
    )
    canonical_tags = JINJA_TAG_PATTERN.findall(canonicalized.text)
    original_by_canonical.update(
        {
            canonical: original_by_canonical.get(canonical, original)
            for canonical, original in canonicalized.original_var_paths_by_canonical.items()
        }
    )
    missing_variables.extend(canonicalized.missing_variables)

    rewritten = xml_text
    for original_tag, canonical_tag in zip(original_tags, canonical_tags):
        if original_tag == canonical_tag:
            continue
        rewritten = _replace_split_text_once(rewritten, original_tag, canonical_tag)
    return rewritten


def _replace_split_text_once(xml_text: str, original: str, replacement: str) -> str:
    separator = r"(?:<[^>]+>)*"
    pattern = separator.join(re.escape(character) for character in original)
    return re.sub(pattern, replacement, xml_text, count=1, flags=re.DOTALL)


def _unique_missing_variables(variables: list[MissingTemplateVariable]) -> list[MissingTemplateVariable]:
    unique: dict[tuple[str, str, str, str], MissingTemplateVariable] = {}
    for variable in variables:
        key = (variable.original_var_path, variable.table_name, variable.field_name, variable.reason)
        unique.setdefault(key, variable)
    return list(unique.values())
