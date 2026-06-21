from __future__ import annotations

from enum import Enum
from pathlib import Path


class TemplateFileType(str, Enum):
    DOCX = "docx"
    XLSX = "xlsx"

    @property
    def suffix(self) -> str:
        return f".{self.value}"

    @property
    def media_type(self) -> str:
        if self is TemplateFileType.XLSX:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


SUPPORTED_TEMPLATE_SUFFIXES = {item.suffix for item in TemplateFileType}


def detect_template_file_type(path_or_filename: str | Path) -> TemplateFileType:
    suffix = Path(path_or_filename).suffix.lower()
    for file_type in TemplateFileType:
        if suffix == file_type.suffix:
            return file_type
    raise ValueError(f"unsupported template file type: {suffix or '<none>'}")


def media_type_for_file(path_or_filename: str | Path) -> str:
    return detect_template_file_type(path_or_filename).media_type
