from __future__ import annotations

import hashlib
import re
from pathlib import Path

INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\s]+')
MAX_OUTPUT_FILENAME_LENGTH = 120
HASH_LENGTH = 6


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    sanitized = INVALID_FILENAME_CHARS.sub(replacement, filename).strip(replacement)
    return sanitized or "file"


def sanitize_stem(stem: str) -> str:
    return sanitize_filename(stem)


def safe_table_filename(table_name: str) -> str:
    return f"{sanitize_filename(table_name)}.xlsx"


def build_safe_output_filename(template_name: str, primary_key_value: str, suffix: str = ".docx") -> str:
    safe_stem = sanitize_filename(f"{template_name}_{primary_key_value}")
    suffix_value = suffix if suffix.startswith(".") else f".{suffix}"
    filename = f"{safe_stem}{suffix_value}"
    if len(filename) <= MAX_OUTPUT_FILENAME_LENGTH:
        return filename

    digest = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:HASH_LENGTH]
    reserved_length = len(suffix_value) + HASH_LENGTH + 1
    stem_limit = MAX_OUTPUT_FILENAME_LENGTH - reserved_length
    truncated_stem = safe_stem[:stem_limit].rstrip("_")
    return f"{truncated_stem}_{digest}{suffix_value}"


def has_path_traversal(value: str) -> bool:
    path = Path(value)
    return path.is_absolute() or ".." in path.parts or any(part in ("", ".") for part in path.parts)
