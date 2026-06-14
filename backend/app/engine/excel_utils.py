from __future__ import annotations

from collections.abc import Iterable


def excel_column_letter(column_index: int) -> str:
    if column_index < 0:
        raise ValueError("excel column index must be greater than or equal to 0")

    number = column_index + 1
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def build_column_index_map(columns: Iterable[str]) -> dict[str, int]:
    return {column: index for index, column in enumerate(columns)}


def build_excel_column_letter_map(columns: Iterable[str]) -> dict[str, str]:
    return {column: excel_column_letter(index) for index, column in enumerate(columns)}
