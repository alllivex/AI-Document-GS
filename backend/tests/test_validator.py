from pathlib import Path
import json
import sys
import zipfile

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.engine.data_loader import LoadedTable, load_data_tables
from app.engine.validator import validate_task
from app.models.template_models import FieldDefinition, RequiredTable, TemplateRequirements


def reset_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    get_settings.cache_clear()
    return get_settings()


def write_template(path: Path, body_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{body_text}</w:t></w:r></w:p></w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def loaded_table(table_name: str, rows: list[dict]) -> LoadedTable:
    dataframe = pd.DataFrame(rows)
    columns = list(dataframe.columns)
    return LoadedTable(
        table_name=table_name,
        source_file=f"{table_name}.xlsx",
        source_file_path=f"/tmp/{table_name}.xlsx",
        dataframe=dataframe,
        columns=columns,
        row_count=len(dataframe.index),
        column_count=len(columns),
        column_index_map={column: index for index, column in enumerate(columns)},
        excel_column_letter_map={column: chr(65 + index) for index, column in enumerate(columns)},
    )


def requirements() -> TemplateRequirements:
    return TemplateRequirements(
        template_id=1,
        template_name="Customer Report",
        template_file="due_diligence.docx",
        template_path="templates/due_diligence.docx",
        main_table="customer_info",
        primary_key_field="customer_id",
        required_tables=[
            RequiredTable(
                table_name="customer_info",
                role="main",
                relation_type="main",
                required=True,
            ),
            RequiredTable(
                table_name="loan_summary",
                role="aux",
                relation_type="one_to_one",
                main_join_key="customer_id",
                table_join_key="customer_id",
                required=True,
            ),
        ],
        fields=[
            FieldDefinition(
                table_name="customer_info",
                table_name_cn="客户信息表",
                field_name="customer_id",
                field_name_cn="客户编号",
                is_primary_key=True,
                required=True,
            ),
            FieldDefinition(
                table_name="customer_info",
                table_name_cn="客户信息表",
                field_name="customer_name",
                field_name_cn="客户名称",
                required=True,
            ),
            FieldDefinition(
                table_name="loan_summary",
                table_name_cn="贷款汇总表",
                field_name="customer_id",
                field_name_cn="客户编号",
                is_primary_key=True,
                required=True,
            ),
            FieldDefinition(
                table_name="loan_summary",
                table_name_cn="贷款汇总表",
                field_name="loan_balance",
                field_name_cn="贷款余额",
                required=True,
            ),
        ],
    )


def valid_tables() -> dict[str, LoadedTable]:
    return {
        "customer_info": loaded_table(
            "customer_info",
            [
                {"customer_id": "C001", "customer_name": "Acme"},
                {"customer_id": "C002", "customer_name": "Beta"},
            ],
        ),
        "loan_summary": loaded_table(
            "loan_summary",
            [
                {"customer_id": "C001", "loan_balance": 1200},
                {"customer_id": "C002", "loan_balance": 800},
            ],
        ),
    }


def item_codes(report) -> set[str]:
    return {item.code for item in report.items}


def test_validate_task_passes_and_writes_validation_report(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    task_id = "task_20260613_153000_a1b2c3"
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_name }} {{ loan_summary.loan_balance }}")

    report = validate_task(task_id, requirements(), valid_tables(), template_path, settings=settings)

    report_path = settings.tasks_dir / task_id / "validation" / "validation_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.status == "passed"
    assert report.summary.error_count == 0
    assert payload["task_id"] == task_id
    assert payload["status"] == "passed"
    assert payload["items"] == []


def test_validate_task_accepts_loaded_tables_from_real_excel_files(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    task_id = "task_20260613_153000_a1b2c3"
    data_dir = settings.tasks_dir / task_id / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"customer_id": "C001", "customer_name": "Acme"},
            {"customer_id": "C002", "customer_name": "Beta"},
        ]
    ).to_excel(data_dir / "customer_info.xlsx", index=False)
    pd.DataFrame(
        [
            {"customer_id": "C001", "loan_balance": 1200},
            {"customer_id": "C002", "loan_balance": 800},
        ]
    ).to_excel(data_dir / "loan_summary.xlsx", index=False)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_name }} {{ loan_summary.loan_balance }}")

    tables = load_data_tables(data_dir, ["customer_info", "loan_summary"])
    report = validate_task(task_id, requirements(), tables, template_path, settings=settings)

    report_path = settings.tasks_dir / task_id / "validation" / "validation_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.status == "passed"
    assert payload["summary"]["error_count"] == 0


def test_validate_task_reports_missing_required_excel(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_name }}")
    tables = {"customer_info": valid_tables()["customer_info"]}

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), tables, template_path, settings=settings)

    assert report.status == "failed"
    assert "missing_required_table" in item_codes(report)


def test_validate_task_reports_empty_and_duplicated_primary_key(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_name }}")
    tables = valid_tables()
    tables["customer_info"] = loaded_table(
        "customer_info",
        [
            {"customer_id": "C001", "customer_name": "Acme"},
            {"customer_id": "", "customer_name": "Blank"},
            {"customer_id": "C001", "customer_name": "Duplicate"},
        ],
    )

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), tables, template_path, settings=settings)

    assert {"empty_primary_key", "duplicated_primary_key"}.issubset(item_codes(report))


def test_validate_task_reports_missing_required_field(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_id }}")
    tables = valid_tables()
    tables["customer_info"] = loaded_table("customer_info", [{"customer_id": "C001"}])

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), tables, template_path, settings=settings)

    assert "missing_required_field" in item_codes(report)


def test_validate_task_reports_missing_template_field(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ loan_summary.missing_balance }}")

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), valid_tables(), template_path, settings=settings)

    assert "missing_field" in item_codes(report)
    missing = next(item for item in report.items if item.code == "missing_field")
    assert missing.table_name == "loan_summary"
    assert missing.field_name == "missing_balance"


def test_validate_task_passes_chinese_template_variables(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ 客户信息表.客户名称 }} {{ 贷款汇总表.贷款余额 }}")

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), valid_tables(), template_path, settings=settings)

    assert report.status == "passed"
    assert report.items == []


def test_validate_task_reports_unknown_chinese_template_field(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ 客户信息表.不存在字段 }}")

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), valid_tables(), template_path, settings=settings)

    assert "missing_field" in item_codes(report)
    missing = next(item for item in report.items if item.code == "missing_field")
    assert missing.table_name == "customer_info"
    assert missing.field_name == "不存在字段"
    assert missing.detail["original_variable_path"] == "客户信息表.不存在字段"


def test_validate_task_reports_one_to_one_multiple_rows(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ loan_summary.loan_balance }}")
    tables = valid_tables()
    tables["loan_summary"] = loaded_table(
        "loan_summary",
        [
            {"customer_id": "C001", "loan_balance": 1200},
            {"customer_id": "C001", "loan_balance": 1300},
        ],
    )

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), tables, template_path, settings=settings)

    assert "one_to_one_multiple_rows" in item_codes(report)


def test_validate_task_passes_docxtpl_table_loop_references(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    req = requirements()
    req.required_tables.append(
        RequiredTable(
            table_name="collateral_info",
            role="aux",
            relation_type="one_to_many",
            main_join_key="customer_id",
            table_join_key="customer_id",
            required=True,
        )
    )
    req.fields.append(FieldDefinition(table_name="collateral_info", field_name="customer_id", required=True))
    req.fields.append(FieldDefinition(table_name="collateral_info", field_name="collateral_name", required=True))
    tables = valid_tables()
    tables["collateral_info"] = loaded_table(
        "collateral_info",
        [
            {"customer_id": "C001", "collateral_name": "Factory"},
            {"customer_id": "C001", "collateral_name": "Equipment"},
        ],
    )
    write_template(
        template_path,
        "{%tr for collateral in collateral_info %}{{ collateral.collateral_name }}{%tr endfor %}",
    )

    report = validate_task("task_20260613_153000_a1b2c3", req, tables, template_path, settings=settings)

    assert report.status == "passed"
    assert "missing_field" not in item_codes(report)


def test_validate_task_reports_unknown_template_table(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ unknown_table.customer_id }}")

    report = validate_task("task_20260613_153000_a1b2c3", requirements(), valid_tables(), template_path, settings=settings)

    assert "missing_field" in item_codes(report)
    missing = next(item for item in report.items if item.code == "missing_field")
    assert missing.table_name == "unknown_table"
    assert missing.field_name == "customer_id"


def test_validate_task_warns_for_missing_optional_table(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    template_path = tmp_path / "templates" / "due_diligence.docx"
    write_template(template_path, "{{ customer_info.customer_name }}")
    req = requirements()
    req.required_tables.append(
        RequiredTable(
            table_name="collateral_info",
            role="aux",
            relation_type="one_to_many",
            main_join_key="customer_id",
            table_join_key="customer_id",
            required=False,
        )
    )

    report = validate_task("task_20260613_153000_a1b2c3", req, valid_tables(), template_path, settings=settings)

    assert report.status == "passed_with_warnings"
    assert "missing_optional_table" in item_codes(report)
