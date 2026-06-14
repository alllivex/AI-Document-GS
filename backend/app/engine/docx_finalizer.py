from __future__ import annotations

from pathlib import Path

from app.engine.ai_block_applier import ApplyAIBlocksInput, ApplyAIBlocksResult, apply_ai_blocks
from app.engine.ai_generator import AIGenerateResult


def finalize_docx(
    rendered_docx_path: Path,
    output_docx_path: Path,
    ai_results: list[AIGenerateResult],
    ai_enabled: bool,
) -> ApplyAIBlocksResult:
    return apply_ai_blocks(
        ApplyAIBlocksInput(
            rendered_docx_path=rendered_docx_path,
            output_docx_path=output_docx_path,
            ai_results=ai_results,
            ai_enabled=ai_enabled,
        )
    )


def finalize_rendered_document(
    rendered_docx_path: Path,
    output_docx_path: Path,
    ai_results: list[AIGenerateResult],
    ai_enabled: bool,
) -> ApplyAIBlocksResult:
    return finalize_docx(
        rendered_docx_path=rendered_docx_path,
        output_docx_path=output_docx_path,
        ai_results=ai_results,
        ai_enabled=ai_enabled,
    )
