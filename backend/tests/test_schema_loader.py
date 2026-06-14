from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.schema_loader import build_translation_maps, load_entity_schema
from app.models.enums import DataType


def write_schema(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_excel(path, index=False)


def test_load_entity_schema_reads_fields_and_translation_maps(tmp_path) -> None:
    schema_path = tmp_path / "entity_schema.xlsx"
    write_schema(
        schema_path,
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
                "table_name": "customer_info",
                "table_name_chinese": "客户信息表",
                "field_name": "customer_name",
                "field_name_chinese": "客户名称",
                "is_primary_key": 0,
                "data_type": "string",
                "required": 1,
            },
        ],
    )

    fields = load_entity_schema(schema_path)
    maps = build_translation_maps(fields)

    assert len(fields) == 2
    assert fields[0].table_name_cn == "客户信息表"
    assert fields[0].data_type == DataType.STRING.value
    assert fields[1].required is True
    assert maps.table_en_to_cn["customer_info"] == "客户信息表"
    assert maps.field_en_to_cn[("customer_info", "customer_name")] == "客户名称"


def test_load_entity_schema_requires_one_primary_key_per_table(tmp_path) -> None:
    schema_path = tmp_path / "entity_schema.xlsx"
    write_schema(
        schema_path,
        [
            {"table_name": "customer_info", "field_name": "customer_id", "is_primary_key": 1},
            {"table_name": "customer_info", "field_name": "customer_name", "is_primary_key": 1},
        ],
    )

    with pytest.raises(ValueError, match="exactly one primary key"):
        load_entity_schema(schema_path)


def test_load_entity_schema_rejects_table_without_primary_key(tmp_path) -> None:
    schema_path = tmp_path / "entity_schema.xlsx"
    write_schema(
        schema_path,
        [
            {"table_name": "customer_info", "field_name": "customer_id", "is_primary_key": 0},
            {"table_name": "customer_info", "field_name": "customer_name", "is_primary_key": 0},
        ],
    )

    with pytest.raises(ValueError, match="exactly one primary key"):
        load_entity_schema(schema_path)
