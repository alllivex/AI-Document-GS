from __future__ import annotations

from pathlib import Path
import re
from typing import Any
import zipfile

from lxml import etree
from pydantic import BaseModel

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
AIBLOCK_PATTERN = re.compile(r"\u00a7AIBLOCK\d+\u00a7")
PROMPT_PATTERN = re.compile(r"prompt\s*=\s*([\"'])([\s\S]*?)\1")


class AIPromptLoadInput(BaseModel):
    template_path: Path


class AIPromptDefinition(BaseModel):
    block_id: str
    marker: str
    prompt_template: str
    comment_id: str | None = None
    selected_text: str = ""


class AITemplateBindingIssue(BaseModel):
    code: str
    message: str
    comment_id: str | None = None
    marker: str | None = None
    selected_text: str = ""


class AIPromptBindingAnalysis(BaseModel):
    prompts: list[AIPromptDefinition]
    issues: list[AITemplateBindingIssue]


def load_ai_prompts(input_data: AIPromptLoadInput) -> list[AIPromptDefinition]:
    return load_ai_prompts_from_template(input_data.template_path)


def load_ai_prompts_from_template(template_docx: Path) -> list[AIPromptDefinition]:
    analysis = analyze_ai_prompt_bindings(template_docx)
    if analysis.issues:
        messages = "; ".join(issue.message for issue in analysis.issues)
        raise ValueError(f"Invalid AI block bindings: {messages}")
    return analysis.prompts


def analyze_ai_prompt_bindings(template_docx: Path) -> AIPromptBindingAnalysis:
    marker_counts = _get_ai_marker_counts(template_docx)
    prompt_comments = _extract_prompt_comments(template_docx)
    selected_text_by_comment_id = _extract_comment_selected_text(template_docx)

    prompts: list[AIPromptDefinition] = []
    issues: list[AITemplateBindingIssue] = []
    bound_markers: dict[str, str] = {}
    markers_with_promptless_comment: set[str] = set()

    for marker, count in marker_counts.items():
        if count > 1:
            issues.append(
                AITemplateBindingIssue(
                    code="duplicate_ai_marker",
                    message=f"AI block marker appears multiple times in template: {marker}",
                    marker=marker,
                )
            )

    for comment_id, prompt_template in sorted(prompt_comments.items(), key=lambda item: _comment_sort_key(item[0])):
        selected_text = selected_text_by_comment_id.get(comment_id, "")
        markers = _find_ai_markers(selected_text)
        if not markers:
            issues.append(
                AITemplateBindingIssue(
                    code="prompt_comment_without_ai_marker",
                    message=f"AI prompt comment does not cover an AI block marker: comment_id={comment_id}",
                    comment_id=comment_id,
                    selected_text=selected_text,
                )
            )
            continue
        if len(markers) > 1:
            issues.append(
                AITemplateBindingIssue(
                    code="prompt_comment_covers_multiple_ai_markers",
                    message=f"AI prompt comment covers multiple AI block markers: comment_id={comment_id}",
                    comment_id=comment_id,
                    selected_text=selected_text,
                )
            )
            continue

        marker = markers[0]
        previous_comment_id = bound_markers.get(marker)
        if previous_comment_id is not None:
            issues.append(
                AITemplateBindingIssue(
                    code="ai_marker_bound_to_multiple_comments",
                    message=(
                        f"AI block marker is bound to multiple prompt comments: "
                        f"{marker}, comment_id={previous_comment_id}, comment_id={comment_id}"
                    ),
                    comment_id=comment_id,
                    marker=marker,
                    selected_text=selected_text,
                )
            )
            continue

        bound_markers[marker] = comment_id
        prompts.append(
            AIPromptDefinition(
                block_id=_block_id_from_marker(marker),
                marker=marker,
                prompt_template=prompt_template,
                comment_id=comment_id,
                selected_text=selected_text,
            )
        )

    for comment_id, selected_text in selected_text_by_comment_id.items():
        if comment_id in prompt_comments:
            continue
        for marker in _find_ai_markers(selected_text):
            markers_with_promptless_comment.add(marker)
            issues.append(
                AITemplateBindingIssue(
                    code="ai_marker_comment_missing_prompt",
                    message=f"AI block marker comment does not contain a valid prompt: {marker}, comment_id={comment_id}",
                    comment_id=comment_id,
                    marker=marker,
                    selected_text=selected_text,
                )
            )

    for marker in marker_counts:
        if marker not in bound_markers:
            if marker in markers_with_promptless_comment:
                continue
            issue_code = "ai_marker_missing_prompt_comment"
            issue_message = f"AI block marker is not covered by a prompt comment: {marker}"
            issues.append(AITemplateBindingIssue(code=issue_code, message=issue_message, marker=marker))

    return AIPromptBindingAnalysis(prompts=prompts, issues=issues)


def get_ai_block_markers_for_template(template_path: Path) -> list[str]:
    return list(_get_ai_marker_counts(template_path).keys())


def extract_prompt_from_comment_text(comment_text: str) -> str:
    match = PROMPT_PATTERN.search(comment_text)
    if match is None:
        raise ValueError('comment does not contain prompt="..."')
    return match.group(2)


def _extract_prompt_comments(template_docx: Path) -> dict[str, str]:
    prompt_comments: dict[str, str] = {}
    for comment_id, comment_text in _extract_all_comments(template_docx).items():
        if "prompt" not in comment_text:
            continue
        try:
            prompt_comments[comment_id] = extract_prompt_from_comment_text(comment_text)
        except ValueError:
            continue
    return prompt_comments


def _extract_all_comments(template_docx: Path) -> dict[str, str]:
    try:
        comments_xml = _read_docx_xml(template_docx, "word/comments.xml")
    except KeyError:
        return {}

    root = etree.fromstring(comments_xml)
    comments: dict[str, str] = {}
    for comment in root.xpath(".//w:comment", namespaces=W_NS):
        comment_id = str(comment.get(f"{{{W_NS['w']}}}id") or "")
        comments[comment_id] = "".join(comment.xpath(".//w:t/text()", namespaces=W_NS))
    return comments


def _extract_comment_selected_text(template_docx: Path) -> dict[str, str]:
    document_xml = _read_docx_xml(template_docx, "word/document.xml")
    root = etree.fromstring(document_xml)
    active_ranges: dict[str, list[str]] = {}
    selected_text_by_comment_id: dict[str, str] = {}

    for element in root.iter():
        local_name = etree.QName(element).localname
        if local_name == "commentRangeStart":
            comment_id = _word_id(element)
            if comment_id:
                active_ranges.setdefault(comment_id, [])
            continue

        if local_name == "t" and element.text:
            for fragments in active_ranges.values():
                fragments.append(element.text)
            continue

        if local_name == "commentRangeEnd":
            comment_id = _word_id(element)
            if comment_id and comment_id in active_ranges:
                selected_text_by_comment_id[comment_id] = "".join(active_ranges.pop(comment_id)).strip()

    return selected_text_by_comment_id


def _get_ai_marker_counts(template_path: Path) -> dict[str, int]:
    document_xml = _read_docx_xml(template_path, "word/document.xml")
    root = etree.fromstring(document_xml)
    text = "".join(root.xpath(".//w:t/text()", namespaces=W_NS))

    marker_counts: dict[str, int] = {}
    for match in AIBLOCK_PATTERN.finditer(text):
        marker = match.group(0)
        marker_counts[marker] = marker_counts.get(marker, 0) + 1
    return marker_counts


def _find_ai_markers(text: str) -> list[str]:
    markers: list[str] = []
    seen: set[str] = set()
    for match in AIBLOCK_PATTERN.finditer(text):
        marker = match.group(0)
        if marker in seen:
            continue
        markers.append(marker)
        seen.add(marker)
    return markers


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
    return marker.strip("\u00a7")


def _word_id(element: Any) -> str:
    return str(element.get(f"{{{W_NS['w']}}}id") or "")
