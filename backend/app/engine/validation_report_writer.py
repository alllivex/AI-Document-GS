from __future__ import annotations

import json
from pathlib import Path

from app.core.config import AppSettings
from app.models.validation_models import ValidationReport
from app.storage.paths import build_task_workspace

VALIDATION_REPORT_FILENAME = "validation_report.json"


def write_validation_report(
    task_id: str,
    report: ValidationReport,
    task_dir: Path | None = None,
    settings: AppSettings | None = None,
) -> Path:
    validation_dir = (
        task_dir / "validation"
        if task_dir is not None
        else build_task_workspace(task_id, settings).validation_dir
    )
    validation_dir.mkdir(parents=True, exist_ok=True)

    report_path = validation_dir / VALIDATION_REPORT_FILENAME
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path
