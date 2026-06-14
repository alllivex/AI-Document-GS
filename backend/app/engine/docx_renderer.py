from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from docx import Document
from docxtpl import DocxTemplate
from jinja2 import Environment
from pydantic import BaseModel


class RenderDocxInput(BaseModel):
    template_path: Path
    context: dict[str, Any]
    output_path: Path


class RenderDocxResult(BaseModel):
    output_path: Path
    success: bool
    error_message: str = ""


def render_docx(input_data: RenderDocxInput) -> RenderDocxResult:
    return render_docx_template(
        template_docx=input_data.template_path,
        context=input_data.context,
        output_docx=input_data.output_path,
    )


def render_docx_template(
    template_docx: Path,
    context: dict[str, Any],
    output_docx: Path,
) -> RenderDocxResult:
    template_path = Path(template_docx)
    output_path = Path(output_docx)
    temp_output_path = output_path.with_name(f".{output_path.name}.{uuid4().hex}.tmp.docx")

    try:
        if not template_path.exists():
            return _failed(output_path, f"Template file not found: {template_path}")
        if not template_path.is_file():
            return _failed(output_path, f"Template path is not a file: {template_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        document = DocxTemplate(str(template_path))
        document.render(context, jinja_env=Environment(autoescape=False))
        document.save(str(temp_output_path))

        # Verify the generated package before exposing it to downstream modules.
        Document(str(temp_output_path))
        temp_output_path.replace(output_path)

        return RenderDocxResult(output_path=output_path, success=True)
    except Exception as exc:
        _remove_if_exists(temp_output_path)
        return _failed(output_path, f"Failed to render docx template '{template_path}': {exc}")


def _failed(output_path: Path, message: str) -> RenderDocxResult:
    return RenderDocxResult(output_path=output_path, success=False, error_message=message)


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
