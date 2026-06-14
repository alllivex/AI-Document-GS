from pathlib import Path
import sys
import zipfile

from docx import Document
from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.ai_prompt_loader import (
    AIPromptLoadInput,
    extract_prompt_from_comment_text,
    get_ai_block_markers_for_template,
    load_ai_prompts,
    load_ai_prompts_from_template,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def write_template_with_ai_comments(path: Path) -> None:
    document = Document()
    document.add_paragraph("Intro §AIBLOCK0§")
    document.add_paragraph("Next §AIBLOCK1§")
    document.save(path)
    add_comments_xml(
        path,
        [
            'prompt="Analyze {{ customer_info.customer_name }}"',
            'prompt="Summarize loan {{ loan_summary.loan_balance }}"',
        ],
    )


def add_comments_xml(path: Path, comment_texts: list[str]) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        files = {name: archive.read(name) for name in archive.namelist()}

    comments_root = etree.Element(f"{{{W_NS}}}comments", nsmap={"w": W_NS})
    for index, comment_text in enumerate(comment_texts):
        comment = etree.SubElement(comments_root, f"{{{W_NS}}}comment")
        comment.set(f"{{{W_NS}}}id", str(index))
        paragraph = etree.SubElement(comment, f"{{{W_NS}}}p")
        run = etree.SubElement(paragraph, f"{{{W_NS}}}r")
        text = etree.SubElement(run, f"{{{W_NS}}}t")
        text.text = comment_text
    files["word/comments.xml"] = etree.tostring(
        comments_root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    content_types = etree.fromstring(files["[Content_Types].xml"])
    override_tag = f"{{{CT_NS}}}Override"
    if not any(element.get("PartName") == "/word/comments.xml" for element in content_types.findall(override_tag)):
        override = etree.Element(override_tag)
        override.set("PartName", "/word/comments.xml")
        override.set("ContentType", "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml")
        content_types.append(override)
    files["[Content_Types].xml"] = etree.tostring(
        content_types,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    rels_path = "word/_rels/document.xml.rels"
    relationships = etree.fromstring(files[rels_path])
    relationship_tag = f"{{{REL_NS}}}Relationship"
    if not any(element.get("Target") == "comments.xml" for element in relationships.findall(relationship_tag)):
        relationship = etree.Element(relationship_tag)
        relationship.set("Id", "rId999")
        relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments")
        relationship.set("Target", "comments.xml")
        relationships.append(relationship)
    files[rels_path] = etree.tostring(
        relationships,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def test_get_ai_block_markers_for_template_reads_markers_in_document_order(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    write_template_with_ai_comments(template_path)

    markers = get_ai_block_markers_for_template(template_path)

    assert markers == ["§AIBLOCK0§", "§AIBLOCK1§"]


def test_load_ai_prompts_from_template_pairs_markers_with_prompt_comments(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    write_template_with_ai_comments(template_path)

    prompts = load_ai_prompts_from_template(template_path)

    assert len(prompts) == 2
    assert prompts[0].block_id == "AIBLOCK0"
    assert prompts[0].marker == "§AIBLOCK0§"
    assert prompts[0].prompt_template == "Analyze {{ customer_info.customer_name }}"
    assert prompts[0].comment_id == "0"
    assert prompts[1].block_id == "AIBLOCK1"
    assert prompts[1].prompt_template == "Summarize loan {{ loan_summary.loan_balance }}"


def test_load_ai_prompts_accepts_input_model(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    write_template_with_ai_comments(template_path)

    prompts = load_ai_prompts(AIPromptLoadInput(template_path=template_path))

    assert [prompt.marker for prompt in prompts] == ["§AIBLOCK0§", "§AIBLOCK1§"]


def test_load_ai_prompts_returns_empty_list_when_template_has_no_comments(tmp_path) -> None:
    template_path = tmp_path / "template.docx"
    document = Document()
    document.add_paragraph("Intro §AIBLOCK0§")
    document.save(template_path)

    assert load_ai_prompts_from_template(template_path) == []


def test_extract_prompt_from_comment_text_requires_prompt_attribute() -> None:
    assert extract_prompt_from_comment_text('prefix prompt="Hello {{ name }}" suffix') == "Hello {{ name }}"
