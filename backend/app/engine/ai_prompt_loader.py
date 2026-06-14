from __future__ import annotations

from pathlib import Path
import re
import zipfile

from lxml import etree
from pydantic import BaseModel

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
AIBLOCK_PATTERN = re.compile(r"§AIBLOCK\d+§")
PROMPT_PATTERN = re.compile(r"prompt\s*=\s*([\"'])([\s\S]*?)\1")


class AIPromptLoadInput(BaseModel):
    template_path: Path


class AIPromptDefinition(BaseModel):
    block_id: str
    marker: str
    prompt_template: str
    comment_id: str | None = None


def load_ai_prompts(input_data: AIPromptLoadInput) -> list[AIPromptDefinition]:
    return load_ai_prompts_from_template(input_data.template_path)


def load_ai_prompts_from_template(template_docx: Path) -> list[AIPromptDefinition]:
    markers = get_ai_block_markers_for_template(template_docx)
    comments = _extract_prompt_comments(template_docx)

    definitions: list[AIPromptDefinition] = []
    for index, (comment_id, prompt_template) in enumerate(comments):
        if index >= len(markers):
            break
        marker = markers[index]
        definitions.append(
            AIPromptDefinition(
                block_id=_block_id_from_marker(marker),
                marker=marker,
                prompt_template=prompt_template,
                comment_id=comment_id,
            )
        )
    return definitions


def get_ai_block_markers_for_template(template_path: Path) -> list[str]:
    document_xml = _read_docx_xml(template_path, "word/document.xml")
    root = etree.fromstring(document_xml)
    text = "".join(root.xpath(".//w:t/text()", namespaces=W_NS))

    markers: list[str] = []
    seen: set[str] = set()
    for match in AIBLOCK_PATTERN.finditer(text):
        marker = match.group(0)
        if marker not in seen:
            markers.append(marker)
            seen.add(marker)
    return markers


def extract_prompt_from_comment_text(comment_text: str) -> str:
    match = PROMPT_PATTERN.search(comment_text)
    if match is None:
        raise ValueError('comment does not contain prompt="..."')
    return match.group(2)


def _extract_prompt_comments(template_docx: Path) -> list[tuple[str, str]]:
    try:
        comments_xml = _read_docx_xml(template_docx, "word/comments.xml")
    except KeyError:
        return []

    root = etree.fromstring(comments_xml)
    prompt_comments: list[tuple[str, str]] = []
    for comment in root.xpath(".//w:comment", namespaces=W_NS):
        comment_id = str(comment.get(f"{{{W_NS['w']}}}id") or "")
        comment_text = "".join(comment.xpath(".//w:t/text()", namespaces=W_NS))
        if "prompt" not in comment_text:
            continue
        try:
            prompt_template = extract_prompt_from_comment_text(comment_text)
        except ValueError:
            continue
        prompt_comments.append((comment_id, prompt_template))

    return sorted(prompt_comments, key=lambda item: _comment_sort_key(item[0]))


def _read_docx_xml(docx_path: Path, internal_path: str) -> bytes:
    if not docx_path.exists():
        raise FileNotFoundError(f"template file not found: {docx_path}")
    with zipfile.ZipFile(docx_path) as archive:
        return archive.read(internal_path)


def _comment_sort_key(comment_id: str) -> tuple[int, str]:
    if comment_id.isdigit():
        return int(comment_id), comment_id
    return 0, comment_id


def _block_id_from_marker(marker: str) -> str:
    return marker.strip("§")
