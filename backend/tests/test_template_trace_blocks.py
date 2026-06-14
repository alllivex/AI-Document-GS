from pathlib import Path
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.template_parser import extract_template_trace_blocks


def write_docx_like_template(path: Path, text: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f"<document><body><p>{text}</p></body></document>")


def test_extract_condition_block_variables_and_text(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    write_docx_like_template(
        template_path,
        "{% if loan_summary.house_eval_amount &lt; loan_summary.loan_balance %}无法清偿{% else %}可清偿{% endif %}",
    )

    blocks = extract_template_trace_blocks(template_path)

    assert len(blocks.conditions) == 1
    condition = blocks.conditions[0]
    assert condition.expression == "loan_summary.house_eval_amount < loan_summary.loan_balance"
    assert condition.used_variables == ["loan_summary.house_eval_amount", "loan_summary.loan_balance"]
    assert condition.if_text == "无法清偿"
    assert condition.else_text == "可清偿"


def test_extract_loop_block_alias_fields(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    write_docx_like_template(
        template_path,
        "{%tr for p in products %}{{ p.product_name }} {{ p.overdue_rate }}{%tr endfor %}",
    )

    blocks = extract_template_trace_blocks(template_path)

    assert len(blocks.loops) == 1
    loop = blocks.loops[0]
    assert loop.table_name == "products"
    assert loop.loop_alias == "p"
    assert loop.used_fields == ["products.overdue_rate", "products.product_name"]
