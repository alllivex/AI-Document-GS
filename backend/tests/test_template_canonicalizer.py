from pathlib import Path
import sys
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.template_canonicalizer import TemplateVariableResolver, canonicalize_docx_template, canonicalize_jinja_text
from app.models.template_models import FieldDefinition


def fields() -> list[FieldDefinition]:
    return [
        FieldDefinition(
            table_name="borrower_info",
            table_name_cn="借款人信息表",
            field_name="LRR_NAME",
            field_name_cn="借款人姓名",
        ),
        FieldDefinition(
            table_name="borrower_info",
            table_name_cn="借款人信息表",
            field_name="LOAN_PRODUCT",
            field_name_cn="贷款产品",
        ),
        FieldDefinition(
            table_name="products",
            table_name_cn="产品明细表",
            field_name="product_name",
            field_name_cn="产品名称",
        ),
    ]


def write_docx_like_template(path: Path, text: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f"<document><body><p>{text}</p></body></document>")


def read_document_xml(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


def test_canonicalize_text_maps_chinese_variable_to_canonical_path() -> None:
    result = canonicalize_jinja_text(
        "{{ 借款人信息表.借款人姓名 }}",
        TemplateVariableResolver(fields()),
    )

    assert result.text == "{{ borrower_info.LRR_NAME }}"
    assert result.original_var_paths_by_canonical == {"borrower_info.LRR_NAME": "借款人信息表.借款人姓名"}
    assert result.missing_variables == []


def test_canonicalize_text_keeps_english_variable() -> None:
    result = canonicalize_jinja_text(
        "{{ borrower_info.LRR_NAME }}",
        TemplateVariableResolver(fields()),
    )

    assert result.text == "{{ borrower_info.LRR_NAME }}"
    assert result.original_var_paths_by_canonical == {"borrower_info.LRR_NAME": "borrower_info.LRR_NAME"}


def test_canonicalize_text_supports_mixed_table_and_field_names() -> None:
    resolver = TemplateVariableResolver(fields())

    chinese_table = canonicalize_jinja_text("{{ 借款人信息表.LRR_NAME }}", resolver)
    chinese_field = canonicalize_jinja_text("{{ borrower_info.借款人姓名 }}", resolver)

    assert chinese_table.text == "{{ borrower_info.LRR_NAME }}"
    assert chinese_field.text == "{{ borrower_info.LRR_NAME }}"


def test_canonicalize_text_supports_chinese_loop_table_and_field() -> None:
    result = canonicalize_jinja_text(
        "{%tr for item in 产品明细表 %}{{ item.产品名称 }}{%tr endfor %}",
        TemplateVariableResolver(fields()),
    )

    assert result.text == "{%tr for item in products %}{{ item.product_name }}{%tr endfor %}"
    assert result.original_var_paths_by_canonical == {"products.product_name": "item.产品名称"}


def test_canonicalize_docx_template_writes_copy_without_mutating_original(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    output_path = tmp_path / "canonical.docx"
    write_docx_like_template(template_path, "{{ 借款人信息表.贷款产品 }}")

    result = canonicalize_docx_template(template_path, output_path, fields())

    assert read_document_xml(template_path) == "<document><body><p>{{ 借款人信息表.贷款产品 }}</p></body></document>"
    assert read_document_xml(output_path) == "<document><body><p>{{ borrower_info.LOAN_PRODUCT }}</p></body></document>"
    assert result.original_var_paths_by_canonical == {"borrower_info.LOAN_PRODUCT": "借款人信息表.贷款产品"}
