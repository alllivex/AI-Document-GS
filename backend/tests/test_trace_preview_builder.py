from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from docx import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.trace_builder import BuildTracePreviewInput, build_trace_and_preview
from app.models.enums import DataType, RelationType
from app.models.trace_models import TraceItem

NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


def make_trace_item(
    trace_id: str,
    var_path: str,
    table_name: str,
    field_name: str,
    display_value: str,
    occurrence_index: int = 0,
) -> TraceItem:
    return TraceItem(
        trace_id=trace_id,
        var_path=var_path,
        table_name=table_name,
        table_name_cn="",
        field_name=field_name,
        field_name_cn="",
        source_file=f"{table_name}.xlsx",
        source_file_path=f"tasks/task_001/data/{table_name}.xlsx",
        pk_field="customer_id",
        pk_value="C001",
        row_index=occurrence_index,
        excel_row_number=occurrence_index + 2,
        column_index=1,
        excel_column_letter="B",
        raw_value=display_value,
        display_value=display_value,
        value_type=DataType.STRING,
        display_format="",
        occurrence_index=occurrence_index,
        source_relation_type=RelationType.MAIN,
        created_at=NOW,
    )


def write_preview_docx(path: Path) -> None:
    document = Document()
    document.add_paragraph("Customer: Acme")
    document.add_paragraph("This unmatched paragraph is still visible.")
    table = document.add_table(rows=3, cols=2)
    table.rows[0].cells[0].text = "Collateral"
    table.rows[0].cells[1].text = "Amount"
    table.rows[1].cells[0].text = "Factory"
    table.rows[1].cells[1].text = "3000.00"
    table.rows[2].cells[0].text = "Unmatched cell"
    table.rows[2].cells[1].text = "No trace"
    document.save(path)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_preview_trace_ids(preview_payload: dict) -> list[str]:
    trace_ids: list[str] = []
    for block in preview_payload["blocks"]:
        if block["type"] == "paragraph":
            trace_ids.extend(run["trace_id"] for run in block["runs"] if run.get("trace_id"))
        elif block["type"] == "table":
            trace_ids.extend(cell["trace_id"] for cell in block["headers"] if cell.get("trace_id"))
            for row in block["rows"]:
                trace_ids.extend(cell["trace_id"] for cell in row if cell.get("trace_id"))
    return trace_ids


def build_input(tmp_path: Path, trace_map: dict[str, list[TraceItem]]) -> BuildTracePreviewInput:
    output_path = tmp_path / "due_diligence_C001.docx"
    write_preview_docx(output_path)
    return BuildTracePreviewInput(
        task_id="task_001",
        doc_id="doc_001",
        template_id=1,
        template_name="due diligence",
        template_file="due_diligence.docx",
        output_file=output_path.name,
        output_path=output_path,
        main_table="customer_info",
        primary_key_field="customer_id",
        primary_key_value="C001",
        trace_map=trace_map,
        final_docx_path=output_path,
    )


def test_build_trace_and_preview_writes_sidecar_json_files(tmp_path) -> None:
    trace_map = {
        "customer_info.customer_name": [
            make_trace_item("trace_customer_name", "customer_info.customer_name", "customer_info", "customer_name", "Acme")
        ],
        "collateral_info.collateral_name": [
            make_trace_item("trace_collateral_name", "collateral_info.collateral_name", "collateral_info", "collateral_name", "Factory")
        ],
    }

    result = build_trace_and_preview(build_input(tmp_path, trace_map))

    assert result.trace_file_path == tmp_path / "due_diligence_C001.trace.json"
    assert result.preview_file_path == tmp_path / "due_diligence_C001.preview.json"
    assert result.trace_count == 2
    assert result.ai_block_count == 0
    assert result.trace_file_path.exists()
    assert result.preview_file_path.exists()


def test_preview_clickable_text_references_trace_json_items(tmp_path) -> None:
    trace_map = {
        "customer_info.customer_name": [
            make_trace_item("trace_customer_name", "customer_info.customer_name", "customer_info", "customer_name", "Acme")
        ],
        "collateral_info.collateral_name": [
            make_trace_item("trace_collateral_name", "collateral_info.collateral_name", "collateral_info", "collateral_name", "Factory")
        ],
    }

    result = build_trace_and_preview(build_input(tmp_path, trace_map))
    trace_payload = load_json(result.trace_file_path)
    preview_payload = load_json(result.preview_file_path)

    trace_ids = {item["trace_id"] for item in trace_payload["trace_items"]}
    preview_trace_ids = set(collect_preview_trace_ids(preview_payload))

    assert preview_trace_ids == {"trace_customer_name", "trace_collateral_name"}
    assert preview_trace_ids <= trace_ids
    customer_trace = next(item for item in trace_payload["trace_items"] if item["trace_id"] == "trace_customer_name")
    assert customer_trace["source_file"] == "customer_info.xlsx"
    assert customer_trace["table_name"] == "customer_info"
    assert customer_trace["field_name"] == "customer_name"
    assert customer_trace["excel_row_number"] == 2
    assert customer_trace["raw_value"] == "Acme"
    assert customer_trace["display_value"] == "Acme"


def test_unmatched_preview_text_is_kept_without_trace_id(tmp_path) -> None:
    trace_map = {
        "customer_info.customer_name": [
            make_trace_item("trace_customer_name", "customer_info.customer_name", "customer_info", "customer_name", "Acme")
        ]
    }

    result = build_trace_and_preview(build_input(tmp_path, trace_map))
    preview_payload = load_json(result.preview_file_path)

    unmatched_block = next(
        block
        for block in preview_payload["blocks"]
        if block["type"] == "paragraph" and block["runs"][0]["text"] == "This unmatched paragraph is still visible."
    )
    assert unmatched_block["runs"] == [{"text": "This unmatched paragraph is still visible.", "trace_id": None, "ai_block_id": None, "style": None}]

    table_block = next(block for block in preview_payload["blocks"] if block["type"] == "table")
    assert table_block["rows"][1][0] == {"text": "Unmatched cell", "trace_id": None, "ai_block_id": None}


def test_repeated_display_values_use_trace_map_order(tmp_path) -> None:
    output_path = tmp_path / "repeat.docx"
    document = Document()
    document.add_paragraph("Acme / Acme")
    document.save(output_path)
    first = make_trace_item("trace_first", "customer_info.customer_name", "customer_info", "customer_name", "Acme", 0)
    second = make_trace_item("trace_second", "related.customer_name", "related", "customer_name", "Acme", 1)

    result = build_trace_and_preview(
        BuildTracePreviewInput(
            task_id="task_001",
            doc_id="doc_001",
            template_id=1,
            template_name="due diligence",
            template_file="due_diligence.docx",
            output_file=output_path.name,
            output_path=output_path,
            main_table="customer_info",
            primary_key_field="customer_id",
            primary_key_value="C001",
            trace_map={
                "customer_info.customer_name": [first],
                "related.customer_name": [second],
            },
            final_docx_path=output_path,
        )
    )

    preview_payload = load_json(result.preview_file_path)
    runs = preview_payload["blocks"][0]["runs"]
    assert [(run["text"], run["trace_id"]) for run in runs] == [
        ("Acme", "trace_first"),
        (" / ", None),
        ("Acme", "trace_second"),
    ]
