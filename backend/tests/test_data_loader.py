from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.data_loader import LoadedTable, load_data_tables
from app.engine.excel_utils import excel_column_letter
from app.models.template_models import FieldDefinition


def write_table(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def test_load_data_tables_reads_multiple_xlsx_with_metadata(tmp_path) -> None:
    write_table(
        tmp_path / "customer_info.xlsx",
        [
            {"customer_id": "C001", "customer_name": "Acme", "region": "Hangzhou"},
            {"customer_id": "C002", "customer_name": "Beta", "region": "Ningbo"},
        ],
    )
    write_table(
        tmp_path / "loan_summary.xlsx",
        [{"customer_id": "C001", "loan_balance": 1200}],
    )

    tables = load_data_tables(tmp_path, ["customer_info", "loan_summary"])

    customer_table = tables["customer_info"]
    assert isinstance(customer_table, LoadedTable)
    assert customer_table.source_file == "customer_info.xlsx"
    assert customer_table.columns == ["customer_id", "customer_name", "region"]
    assert customer_table.row_count == 2
    assert customer_table.column_count == 3
    assert customer_table.column_index_map == {
        "customer_id": 0,
        "customer_name": 1,
        "region": 2,
    }
    assert customer_table.excel_column_letter_map == {
        "customer_id": "A",
        "customer_name": "B",
        "region": "C",
    }
    assert customer_table.dataframe.loc[0, "customer_name"] == "Acme"
    assert tables["loan_summary"].row_count == 1


def test_excel_column_letter_supports_multi_letter_columns() -> None:
    assert excel_column_letter(0) == "A"
    assert excel_column_letter(25) == "Z"
    assert excel_column_letter(26) == "AA"
    assert excel_column_letter(27) == "AB"


def test_load_data_tables_reports_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="customer_info.*customer_info.xlsx"):
        load_data_tables(tmp_path, ["customer_info"])


def test_load_data_tables_rejects_empty_excel(tmp_path) -> None:
    pd.DataFrame(columns=["customer_id", "customer_name"]).to_excel(
        tmp_path / "customer_info.xlsx",
        index=False,
    )

    with pytest.raises(ValueError, match="customer_info.*empty"):
        load_data_tables(tmp_path, ["customer_info"])


def test_load_data_tables_rejects_excel_without_header(tmp_path) -> None:
    pd.DataFrame([[None, None], ["C001", "Acme"]]).to_excel(
        tmp_path / "customer_info.xlsx",
        index=False,
        header=False,
    )

    with pytest.raises(ValueError, match="customer_info.*no header row"):
        load_data_tables(tmp_path, ["customer_info"])


def test_load_data_tables_rejects_duplicate_headers(tmp_path) -> None:
    pd.DataFrame([["C001", "Acme"]], columns=["customer_id", "customer_id"]).to_excel(
        tmp_path / "customer_info.xlsx",
        index=False,
    )

    with pytest.raises(ValueError, match="customer_info.*duplicate header columns.*customer_id"):
        load_data_tables(tmp_path, ["customer_info"])


def customer_fields() -> list[FieldDefinition]:
    return [
        FieldDefinition(
            table_name="customer_info",
            table_name_cn="客户信息表",
            field_name="customer_id",
            field_name_cn="客户编号",
            is_primary_key=True,
        ),
        FieldDefinition(
            table_name="customer_info",
            table_name_cn="客户信息表",
            field_name="customer_name",
            field_name_cn="客户姓名",
        ),
    ]


def test_load_data_table_maps_chinese_headers_to_schema_field_names(tmp_path) -> None:
    write_table(tmp_path / "customer_info.xlsx", [{"客户编号": "C001", "客户姓名": "张三"}])

    table = load_data_tables(tmp_path, ["customer_info"], customer_fields())["customer_info"]

    assert table.columns == ["customer_id", "customer_name"]
    assert table.dataframe.loc[0, "customer_name"] == "张三"
    assert table.column_index_map == {"customer_id": 0, "customer_name": 1}
    assert table.excel_column_letter_map == {"customer_id": "A", "customer_name": "B"}


def test_load_data_table_accepts_mixed_english_and_chinese_headers(tmp_path) -> None:
    write_table(tmp_path / "customer_info.xlsx", [{"customer_id": "C001", "客户姓名": "张三"}])

    table = load_data_tables(tmp_path, ["customer_info"], customer_fields())["customer_info"]

    assert table.columns == ["customer_id", "customer_name"]


def test_load_data_table_rejects_headers_mapping_to_same_field(tmp_path) -> None:
    write_table(
        tmp_path / "customer_info.xlsx",
        [{"customer_id": "C001", "客户编号": "C002", "客户姓名": "张三"}],
    )

    with pytest.raises(ValueError, match="after schema mapping.*customer_id <- customer_id, 客户编号"):
        load_data_tables(tmp_path, ["customer_info"], customer_fields())


def test_load_data_table_rejects_ambiguous_schema_chinese_names(tmp_path) -> None:
    write_table(tmp_path / "customer_info.xlsx", [{"编号": "C001"}])
    fields = [
        FieldDefinition(table_name="customer_info", field_name="customer_id", field_name_cn="编号"),
        FieldDefinition(table_name="customer_info", field_name="legacy_id", field_name_cn="编号"),
    ]

    with pytest.raises(ValueError, match="ambiguous field header aliases.*编号"):
        load_data_tables(tmp_path, ["customer_info"], fields)


def test_load_data_table_rejects_chinese_alias_colliding_with_english_name(tmp_path) -> None:
    write_table(tmp_path / "customer_info.xlsx", [{"customer_id": "C001"}])
    fields = [
        FieldDefinition(table_name="customer_info", field_name="customer_id", field_name_cn="客户编号"),
        FieldDefinition(table_name="customer_info", field_name="legacy_id", field_name_cn="customer_id"),
    ]

    with pytest.raises(ValueError, match="ambiguous field header aliases.*customer_id"):
        load_data_tables(tmp_path, ["customer_info"], fields)
