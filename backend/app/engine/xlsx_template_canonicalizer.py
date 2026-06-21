from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from app.engine.template_canonicalizer import MissingTemplateVariable
from app.engine.xlsx_template_parser import XlsxCellTemplate, analyze_xlsx_template
from app.models.template_models import FieldDefinition


@dataclass(frozen=True)
class CanonicalXlsxTemplateResult:
    output_path: Path
    sheet_name: str
    cells: tuple[XlsxCellTemplate, ...]
    original_var_paths_by_canonical: dict[str, str]
    missing_variables: tuple[MissingTemplateVariable, ...]


def canonicalize_xlsx_template(
    template_path: Path,
    output_path: Path,
    fields: list[FieldDefinition],
) -> CanonicalXlsxTemplateResult:
    analysis = analyze_xlsx_template(template_path, fields)
    if analysis.issues:
        messages = "; ".join(issue[1] for issue in analysis.issues)
        raise ValueError(messages)

    workbook = load_workbook(template_path, data_only=False)
    worksheet = workbook.worksheets[0]
    for cell_template in analysis.cells:
        worksheet[cell_template.coordinate].value = cell_template.canonical_text

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    workbook.close()
    return CanonicalXlsxTemplateResult(
        output_path=output_path,
        sheet_name=analysis.sheet_name,
        cells=analysis.cells,
        original_var_paths_by_canonical=analysis.original_var_paths_by_canonical,
        missing_variables=analysis.missing_variables,
    )
