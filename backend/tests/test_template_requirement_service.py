from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.errors import AppError
from app.db.connection import get_connection
from app.db.init_db import init_db
from app.engine.template_requirement_service import TemplateRequirementService, get_template_requirements

NOW = "2026-06-14T12:00:00+00:00"


def seed_template_config(connection) -> None:
    connection.execute(
        """
        INSERT INTO templates (
            id, template_name, template_file, template_path, main_table,
            output_name_pattern, ai_enabled_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            "客户尽调报告",
            "due_diligence.docx",
            "templates/due_diligence.docx",
            "customer_info",
            "{template_name}_{primary_key_value}.docx",
            1,
            1,
            NOW,
            NOW,
        ),
    )
    connection.executemany(
        """
        INSERT INTO template_tables (
            template_id, table_name, table_name_cn, role, relation_type,
            main_join_key, table_join_key, required, sort_order, description,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "customer_info", "客户信息表", "main", "main", "", "", 1, 0, "", NOW, NOW),
            (
                1,
                "loan_summary",
                "贷款汇总表",
                "aux",
                "one_to_one",
                "customer_id",
                "customer_id",
                1,
                1,
                "",
                NOW,
                NOW,
            ),
        ],
    )
    connection.executemany(
        """
        INSERT INTO fields (
            table_name, table_name_cn, field_name, field_name_cn, data_type,
            is_primary_key, required, display_format, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("customer_info", "客户信息表", "customer_id", "客户编号", "string", 1, 1, "", "", NOW, NOW),
            ("customer_info", "客户信息表", "customer_name", "客户名称", "string", 0, 1, "", "", NOW, NOW),
            ("loan_summary", "贷款汇总表", "customer_id", "客户编号", "string", 1, 1, "", "", NOW, NOW),
            ("loan_summary", "贷款汇总表", "loan_balance", "贷款余额", "amount", 0, 1, "amount_2", "", NOW, NOW),
        ],
    )


def test_get_template_requirements_returns_tables_keys_and_fields(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"
    init_db(database_path)

    with get_connection(database_path) as connection:
        seed_template_config(connection)
        service = TemplateRequirementService(connection)

        requirements = service.get_template_requirements(1)

    assert requirements.template_id == 1
    assert requirements.template_name == "客户尽调报告"
    assert requirements.template_file == "due_diligence.docx"
    assert requirements.main_table == "customer_info"
    assert requirements.primary_key_field == "customer_id"

    assert [table.table_name for table in requirements.required_tables] == ["customer_info", "loan_summary"]
    aux_table = requirements.required_tables[1]
    assert aux_table.relation_type == "one_to_one"
    assert aux_table.main_join_key == "customer_id"
    assert aux_table.table_join_key == "customer_id"

    field_paths = {(field.table_name, field.field_name) for field in requirements.fields}
    assert ("customer_info", "customer_name") in field_paths
    assert ("loan_summary", "loan_balance") in field_paths


def test_get_template_requirements_function_uses_service(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"
    init_db(database_path)

    with get_connection(database_path) as connection:
        seed_template_config(connection)
        requirements = get_template_requirements(connection, 1)

    assert requirements.primary_key_field == "customer_id"


def test_template_id_not_found_raises_template_not_found(tmp_path) -> None:
    database_path = tmp_path / "config" / "db.sqlite"
    init_db(database_path)

    with get_connection(database_path) as connection:
        service = TemplateRequirementService(connection)
        with pytest.raises(AppError) as exc_info:
            service.get_template_requirements(999)

    assert exc_info.value.code == "TEMPLATE_NOT_FOUND"
    assert exc_info.value.status_code == 404
    assert exc_info.value.details == {"template_id": 999}
