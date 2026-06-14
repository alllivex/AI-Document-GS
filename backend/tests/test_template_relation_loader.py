from pathlib import Path
import sqlite3
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.config_sync import sync_config_to_db
from app.engine.template_relation_loader import load_template_relation


def write_schema(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "table_name": "customer_info",
                "table_name_chinese": "客户信息表",
                "field_name": "customer_id",
                "field_name_chinese": "客户编号",
                "is_primary_key": 1,
                "data_type": "string",
            },
            {
                "table_name": "loan_summary",
                "table_name_chinese": "贷款汇总表",
                "field_name": "customer_id",
                "field_name_chinese": "客户编号",
                "is_primary_key": 1,
                "data_type": "string",
            },
        ]
    ).to_excel(path, index=False)


def write_relation(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def valid_relation_rows() -> list[dict]:
    return [
        {
            "template_id": 1,
            "template_name": "客户尽调报告",
            "template_file": "due_diligence.docx",
            "table_name": "customer_info",
            "table_name_chinese": "客户信息表",
            "role": "main",
        },
        {
            "template_id": 1,
            "template_name": "客户尽调报告",
            "template_file": "due_diligence.docx",
            "table_name": "loan_summary",
            "table_name_chinese": "贷款汇总表",
            "role": "aux",
            "relation_type": "one_to_one",
            "main_join_key": "customer_id",
            "table_join_key": "customer_id",
            "required": 1,
        },
    ]


def test_load_template_relation_reads_relations_and_defaults(tmp_path) -> None:
    relation_path = tmp_path / "template_relation.xlsx"
    write_relation(relation_path, valid_relation_rows())

    relations = load_template_relation(relation_path)

    assert len(relations) == 2
    assert relations[0].role == "main"
    assert relations[0].relation_type == "main"
    assert relations[1].relation_type == "one_to_one"


def test_load_template_relation_requires_exactly_one_main_table(tmp_path) -> None:
    relation_path = tmp_path / "template_relation.xlsx"
    rows = valid_relation_rows()
    rows[1]["role"] = "main"
    write_relation(relation_path, rows)

    with pytest.raises(ValueError, match="exactly one main table"):
        load_template_relation(relation_path)


def test_sync_config_to_db_writes_fields_templates_and_template_tables(tmp_path) -> None:
    schema_path = tmp_path / "entity_schema.xlsx"
    relation_path = tmp_path / "template_relation.xlsx"
    database_path = tmp_path / "config" / "db.sqlite"
    write_schema(schema_path)
    write_relation(relation_path, valid_relation_rows())

    sync_config_to_db(schema_path, relation_path, database_path)

    with sqlite3.connect(database_path) as connection:
        field_count = connection.execute("SELECT COUNT(*) FROM fields").fetchone()[0]
        template = connection.execute(
            "SELECT id, template_name, template_file, template_path, main_table FROM templates WHERE id = ?",
            (1,),
        ).fetchone()
        template_table_count = connection.execute("SELECT COUNT(*) FROM template_tables").fetchone()[0]
        relation = connection.execute(
            "SELECT relation_type, main_join_key, table_join_key FROM template_tables WHERE table_name = ?",
            ("loan_summary",),
        ).fetchone()

    assert field_count == 2
    assert template == (1, "客户尽调报告", "due_diligence.docx", "templates/due_diligence.docx", "customer_info")
    assert template_table_count == 2
    assert relation == ("one_to_one", "customer_id", "customer_id")
