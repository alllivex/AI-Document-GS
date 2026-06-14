from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.context_builder import build_report_contexts
from app.engine.data_loader import LoadedTable
from app.engine.value_formatter import TraceValue
from app.models.enums import DataType, RelationType, TableRole
from app.models.template_models import FieldDefinition, RequiredTable, TemplateRequirements
from app.models.trace_models import TraceItem

NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


def make_loaded_table(table_name: str, rows: list[dict]) -> LoadedTable:
    dataframe = pd.DataFrame(rows)
    columns = list(dataframe.columns)
    return LoadedTable(
        table_name=table_name,
        source_file=f"{table_name}.xlsx",
        source_file_path=f"tasks/task_001/data/{table_name}.xlsx",
        dataframe=dataframe,
        columns=columns,
        row_count=len(dataframe.index),
        column_count=len(columns),
        column_index_map={column: index for index, column in enumerate(columns)},
        excel_column_letter_map={column: chr(65 + index) for index, column in enumerate(columns)},
    )


def make_requirements() -> TemplateRequirements:
    return TemplateRequirements(
        template_id=1,
        template_name="due diligence",
        template_file="due_diligence.docx",
        template_path="templates/due_diligence.docx",
        main_table="customer_info",
        primary_key_field="customer_id",
        required_tables=[
            RequiredTable(
                table_name="customer_info",
                role=TableRole.MAIN,
                relation_type=RelationType.MAIN,
                required=True,
            ),
            RequiredTable(
                table_name="loan_summary",
                role=TableRole.AUX,
                relation_type=RelationType.ONE_TO_ONE,
                main_join_key="customer_id",
                table_join_key="customer_id",
                required=True,
            ),
            RequiredTable(
                table_name="collateral_info",
                role=TableRole.AUX,
                relation_type=RelationType.ONE_TO_MANY,
                main_join_key="customer_id",
                table_join_key="customer_id",
                required=True,
            ),
        ],
        fields=[
            FieldDefinition(
                table_name="customer_info",
                field_name="customer_id",
                data_type=DataType.STRING,
                is_primary_key=True,
            ),
            FieldDefinition(table_name="customer_info", field_name="customer_name", data_type=DataType.STRING),
            FieldDefinition(table_name="customer_info", field_name="industry", data_type=DataType.STRING),
            FieldDefinition(table_name="loan_summary", field_name="customer_id", data_type=DataType.STRING),
            FieldDefinition(
                table_name="loan_summary",
                field_name="loan_balance",
                data_type=DataType.AMOUNT,
                display_format="amount_2",
            ),
            FieldDefinition(table_name="loan_summary", field_name="bad_rate", data_type=DataType.PERCENT),
            FieldDefinition(table_name="collateral_info", field_name="customer_id", data_type=DataType.STRING),
            FieldDefinition(table_name="collateral_info", field_name="collateral_name", data_type=DataType.STRING),
            FieldDefinition(
                table_name="collateral_info",
                field_name="eval_amount",
                data_type=DataType.AMOUNT,
                display_format="amount_2",
            ),
        ],
    )


def make_tables() -> dict[str, LoadedTable]:
    return {
        "customer_info": make_loaded_table(
            "customer_info",
            [
                {"customer_id": "C001", "customer_name": "Acme", "industry": "Manufacturing"},
                {"customer_id": "C002", "customer_name": "Beta", "industry": "Retail"},
                {"customer_id": "C003", "customer_name": "Gamma", "industry": "Construction"},
            ],
        ),
        "loan_summary": make_loaded_table(
            "loan_summary",
            [
                {"customer_id": "C001", "loan_balance": 1200, "bad_rate": 0.018},
                {"customer_id": "C002", "loan_balance": 800, "bad_rate": 0.005},
                {"customer_id": "C003", "loan_balance": 1500, "bad_rate": 0.032},
            ],
        ),
        "collateral_info": make_loaded_table(
            "collateral_info",
            [
                {"customer_id": "C001", "collateral_name": "Factory", "eval_amount": 3000},
                {"customer_id": "C001", "collateral_name": "Equipment", "eval_amount": 500},
                {"customer_id": "C002", "collateral_name": "Shop", "eval_amount": 1200},
            ],
        ),
    }


def test_build_report_contexts_outputs_one_bundle_per_main_row() -> None:
    bundles = build_report_contexts(make_requirements(), make_tables(), task_id="task_001")

    assert len(bundles) == 3
    assert [bundle.primary_key_value for bundle in bundles] == ["C001", "C002", "C003"]
    assert all(bundle.doc_id.startswith("doc_") for bundle in bundles)


def test_context_uses_real_main_table_name_and_never_data_alias() -> None:
    bundle = build_report_contexts(make_requirements(), make_tables(), task_id="task_001")[0]

    assert "data" not in bundle.context
    assert bundle.context["customer_info"]["customer_name"] == "Acme"
    assert bundle.context["customer_info"]["industry"] == "Manufacturing"
    assert "customer_info.customer_name" in bundle.trace_map
    assert "data.customer_name" not in bundle.trace_map


def test_auxiliary_tables_use_dict_for_one_to_one_and_list_for_one_to_many() -> None:
    first, _, third = build_report_contexts(make_requirements(), make_tables(), task_id="task_001")

    assert first.context["loan_summary"] == {
        "customer_id": "C001",
        "loan_balance": "1200.00",
        "bad_rate": "1.80%",
    }
    assert isinstance(first.context["loan_summary"], dict)
    assert isinstance(first.context["collateral_info"], list)
    assert [item["collateral_name"] for item in first.context["collateral_info"]] == ["Factory", "Equipment"]
    assert third.context["collateral_info"] == []


def test_each_context_field_has_trace_item() -> None:
    bundle = build_report_contexts(make_requirements(), make_tables(), task_id="task_001")[0]

    expected_paths = {
        "customer_info.customer_id",
        "customer_info.customer_name",
        "customer_info.industry",
        "loan_summary.customer_id",
        "loan_summary.loan_balance",
        "loan_summary.bad_rate",
        "collateral_info.customer_id",
        "collateral_info.collateral_name",
        "collateral_info.eval_amount",
    }
    assert expected_paths <= set(bundle.trace_map)

    for var_path, trace_items in bundle.trace_map.items():
        assert trace_items
        assert all(isinstance(item, TraceItem) for item in trace_items)
        assert all(item.var_path == var_path for item in trace_items)

    collateral_names = bundle.trace_map["collateral_info.collateral_name"]
    assert [item.display_value for item in collateral_names] == ["Factory", "Equipment"]
    assert [item.occurrence_index for item in collateral_names] == [0, 1]
    assert all(item.source_relation_type == "one_to_many" for item in collateral_names)


def test_source_rows_keep_raw_values_separate_from_display_context() -> None:
    bundle = build_report_contexts(make_requirements(), make_tables(), task_id="task_001")[0]

    assert bundle.context["loan_summary"]["loan_balance"] == "1200.00"
    assert isinstance(bundle.context["loan_summary"]["loan_balance"], TraceValue)
    assert bundle.source_rows["loan_summary"]["loan_balance"] == 1200
    trace_item = bundle.trace_map["loan_summary.loan_balance"][0]
    assert trace_item.raw_value == 1200
    assert trace_item.display_value == "1200.00"
    assert trace_item.excel_column_letter == "B"


def test_trace_value_uses_raw_values_for_numeric_comparison() -> None:
    house_eval_amount = TraceValue(raw_value=900, display_value="900", trace_id="trace_house")
    loan_balance = TraceValue(raw_value=1250, display_value="1250", trace_id="trace_loan")

    assert house_eval_amount < loan_balance
    assert str(house_eval_amount) == "900"
