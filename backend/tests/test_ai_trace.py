from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from docx import Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.ai_client import WORD_READY_SYSTEM_PROMPT
from app.engine.trace_builder import BuildTracePreviewInput, build_trace_and_preview
from app.models.enums import AIBlockStatus, DataType, RelationType
from app.models.trace_models import AIBlockTrace, TraceItem

NOW = datetime(2026, 6, 14, 12, 0, tzinfo=timezone.utc)


def make_trace_item(trace_id: str, var_path: str, field_name: str, display_value: str, raw_value: float) -> TraceItem:
    return TraceItem(
        trace_id=trace_id,
        var_path=var_path,
        table_name="branch_main",
        table_name_cn="支行主表",
        field_name=field_name,
        field_name_cn=field_name,
        source_file="branch_main.xlsx",
        source_file_path="tasks/task_001/data/branch_main.xlsx",
        pk_field="branch_name",
        pk_value="A支行",
        row_index=0,
        excel_row_number=2,
        column_index=1,
        excel_column_letter="D",
        raw_value=raw_value,
        display_value=display_value,
        value_type=DataType.NUMBER,
        display_format="",
        occurrence_index=0,
        source_relation_type=RelationType.MAIN,
        created_at=NOW,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ai_trace_is_written_with_inputs_knowledge_refs_and_preview_block(tmp_path) -> None:
    output_path = tmp_path / "ai_doc.docx"
    document = Document()
    document.add_paragraph("风险分析显示，不良环比0.12、同比0.35均有上升，应加强贷后监测。")
    document.save(output_path)

    bad_mom = make_trace_item("trace_bad_mom", "branch_main.bad_mom", "bad_mom", "0.12", 0.12)
    bad_yoy = make_trace_item("trace_bad_yoy", "branch_main.bad_yoy", "bad_yoy", "0.35", 0.35)
    ai_block = AIBlockTrace(
        block_id="AIBLOCK0",
        marker="搂AIBLOCK0搂",
        status=AIBlockStatus.SUCCESS,
        original_block_text="搂AIBLOCK0搂基于不良环比{{ branch_main.bad_mom }}、同比{{ branch_main.bad_yoy }}撰写建议。",
        prompt_template=(
            "基于{kb:puhui_daikou_buliang}知识库，以及不良环比{{ branch_main.bad_mom }}、"
            "同比{{ branch_main.bad_yoy }}数据，分析风险并给出建议。"
        ),
        prompt_rendered="基于{kb:puhui_daikou_buliang}知识库，以及不良环比0.12、同比0.35数据，分析风险并给出建议。",
        model="deepseek-chat",
        input_variables=[],
        generated_text="风险分析显示，不良环比0.12、同比0.35均有上升，应加强贷后监测。",
        error_message="",
        started_at=NOW,
        completed_at=NOW,
    )

    result = build_trace_and_preview(
        BuildTracePreviewInput(
            task_id="task_001",
            doc_id="doc_001",
            template_id=1,
            template_name="AI测试模板",
            template_file="ai_template.docx",
            output_file=output_path.name,
            output_path=output_path,
            main_table="branch_main",
            primary_key_field="branch_name",
            primary_key_value="A支行",
            trace_map={
                "branch_main.bad_mom": [bad_mom],
                "branch_main.bad_yoy": [bad_yoy],
            },
            ai_blocks=[ai_block],
            final_docx_path=output_path,
        )
    )

    trace_payload = load_json(result.trace_file_path)
    preview_payload = load_json(result.preview_file_path)

    ai_trace = trace_payload["ai_traces"][0]
    assert ai_trace["trace_kind"] == "ai"
    assert ai_trace["block_id"] == "AIBLOCK0"
    assert ai_trace["status"] == "success"
    assert [item["var_path"] for item in ai_trace["input_variables"]] == [
        "branch_main.bad_mom",
        "branch_main.bad_yoy",
    ]
    assert ai_trace["input_variables"][0]["trace_id"] == "trace_bad_mom"
    assert ai_trace["knowledge_refs"] == [{"kb_name": "puhui_daikou_buliang", "retrieval_enabled": False, "chunk_id": None, "doc_name": None, "score": None, "excerpt": None}]

    paragraph = preview_payload["blocks"][0]
    assert paragraph["block_trace_id"] == ai_trace["trace_id"]
    assert paragraph["block_trace_kind"] == "ai"
    field_runs = [run for run in paragraph["runs"] if run.get("trace_kind") == "field"]
    assert {run["trace_id"] for run in field_runs} == {"trace_bad_mom", "trace_bad_yoy"}


def test_ai_prompt_system_prompt_rejects_markdown() -> None:
    assert "Do not use Markdown formatting" in WORD_READY_SYSTEM_PROMPT
    assert "Word business report" in WORD_READY_SYSTEM_PROMPT
