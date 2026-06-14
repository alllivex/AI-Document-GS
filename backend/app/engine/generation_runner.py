from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import traceback
from typing import Any

from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.core.errors import AppError
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.task_repository import TaskRepository
from app.engine.ai_block_applier import ApplyAIBlocksResult
from app.engine.ai_generator import AIGenerateInput, AIGenerateResult, generate_ai_text
from app.engine.ai_prompt_loader import load_ai_prompts_from_template
from app.engine.context_builder import ReportContextBundle, build_report_contexts
from app.engine.data_loader import LoadedTable, load_data_tables
from app.engine.docx_finalizer import finalize_docx
from app.engine.docx_renderer import RenderDocxResult, render_docx_template
from app.engine.template_requirement_service import TemplateRequirementService
from app.engine.trace_builder import BuildTracePreviewInput, BuildTracePreviewResult, build_trace_and_preview
from app.engine.validator import validate_task
from app.models.enums import AIStatus, DocumentStatus, TaskStatus, ValidationStatus
from app.models.task_models import DocumentRecord, OutputSummary, TaskMeta
from app.models.template_models import TemplateRequirements
from app.storage.paths import create_task_workspace
from app.storage.safe_filename import build_safe_output_filename


class GenerateTaskInput(BaseModel):
    task_id: str
    force: bool = False
    ai_enabled: bool = True


class GenerateTaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    total_rows: int
    success_count: int
    failed_count: int
    document_ids: list[str]
    error_message: str = ""


@dataclass(frozen=True)
class GenerationDependencies:
    load_data_tables: Callable[[Path, list[str]], dict[str, LoadedTable]] = load_data_tables
    validate_task: Callable[..., Any] = validate_task
    build_report_contexts: Callable[..., list[ReportContextBundle]] = build_report_contexts
    render_docx_template: Callable[[Path, dict[str, Any], Path], RenderDocxResult] = render_docx_template
    load_ai_prompts_from_template: Callable[[Path], list[Any]] = load_ai_prompts_from_template
    generate_ai_text: Callable[..., AIGenerateResult] = generate_ai_text
    finalize_docx: Callable[[Path, Path, list[AIGenerateResult], bool], ApplyAIBlocksResult] = finalize_docx
    build_trace_and_preview: Callable[[BuildTracePreviewInput], BuildTracePreviewResult] = build_trace_and_preview


def generate_task(
    input_data: GenerateTaskInput,
    *,
    connection: sqlite3.Connection,
    settings: AppSettings | None = None,
    dependencies: GenerationDependencies | None = None,
) -> GenerateTaskResult:
    runner = GenerationRunner(connection, settings=settings, dependencies=dependencies)
    return runner.generate(input_data)


class GenerationRunner:
    def __init__(
        self,
        connection: sqlite3.Connection,
        settings: AppSettings | None = None,
        dependencies: GenerationDependencies | None = None,
    ) -> None:
        self.connection = connection
        self.settings = settings or get_settings()
        self.dependencies = dependencies or GenerationDependencies()
        self.task_repository = TaskRepository(connection)
        self.document_repository = DocumentRepository(connection)
        self.requirement_service = TemplateRequirementService(connection)

    def generate(self, input_data: GenerateTaskInput) -> GenerateTaskResult:
        task = self.task_repository.get(input_data.task_id)
        if task is None:
            raise AppError(
                code="TASK_NOT_FOUND",
                message=f"Task not found: {input_data.task_id}",
                status_code=404,
                details={"task_id": input_data.task_id},
            )
        _assert_can_generate(task.status, input_data.force)

        workspace = create_task_workspace(task.task_id, self.settings)
        started_at = _utc_now()
        self._update_task_running(task.task_id, started_at)
        self._log(task.task_id, "", "info", "start", "Generation started.")

        try:
            requirements = self.requirement_service.get_template_requirements(task.template_id)
            template_path = _resolve_project_path(requirements.template_path, self.settings.project_root)
            table_names = [table.table_name for table in requirements.required_tables]
            loaded_tables = self.dependencies.load_data_tables(workspace.data_dir, table_names)

            validation_report = self.dependencies.validate_task(
                task.task_id,
                requirements,
                loaded_tables,
                template_path,
                task_dir=workspace.task_dir,
                settings=self.settings,
            )
            if validation_report.status == ValidationStatus.FAILED:
                error_message = "Generation stopped because validation failed."
                completed_at = _utc_now()
                self._update_task_summary(
                    task.task_id,
                    status=TaskStatus.FAILED,
                    total_rows=0,
                    success_count=0,
                    failed_count=0,
                    error_message=error_message,
                    completed_at=completed_at,
                )
                self._update_meta(task.task_id, TaskStatus.FAILED, [], 0, 0, 0, completed_at)
                self._log(task.task_id, "", "error", "validation", error_message)
                self.connection.commit()
                return GenerateTaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    total_rows=0,
                    success_count=0,
                    failed_count=0,
                    document_ids=[],
                    error_message=error_message,
                )

            bundles = self.dependencies.build_report_contexts(requirements, loaded_tables, task_id=task.task_id)
            result = self._generate_bundles(
                task_id=task.task_id,
                requirements=requirements,
                template_path=template_path,
                bundles=bundles,
                ai_enabled=bool(input_data.ai_enabled and task.ai_enabled),
            )
            self.connection.commit()
            return result
        except Exception as exc:
            error_message = str(exc)
            completed_at = _utc_now()
            self._update_task_summary(
                task.task_id,
                status=TaskStatus.FAILED,
                total_rows=0,
                success_count=0,
                failed_count=0,
                error_message=error_message,
                completed_at=completed_at,
            )
            self._update_meta(task.task_id, TaskStatus.FAILED, [], 0, 0, 0, completed_at)
            self._log(task.task_id, "", "error", "generation", "Generation failed before document loop.", traceback.format_exc())
            self.connection.commit()
            return GenerateTaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                total_rows=0,
                success_count=0,
                failed_count=0,
                document_ids=[],
                error_message=error_message,
            )

    def _generate_bundles(
        self,
        *,
        task_id: str,
        requirements: TemplateRequirements,
        template_path: Path,
        bundles: list[ReportContextBundle],
        ai_enabled: bool,
    ) -> GenerateTaskResult:
        workspace = create_task_workspace(task_id, self.settings)
        document_ids: list[str] = []
        success_count = 0
        failed_count = 0

        for bundle in bundles:
            try:
                document_record = self._generate_one_document(
                    task_id=task_id,
                    requirements=requirements,
                    template_path=template_path,
                    bundle=bundle,
                    ai_enabled=ai_enabled,
                )
                document_ids.append(document_record.doc_id)
                success_count += 1
                self._log(task_id, bundle.doc_id, "info", "document", "Document generated successfully.")
            except Exception:
                failed_count += 1
                self._log(
                    task_id,
                    bundle.doc_id,
                    "error",
                    "document",
                    f"Document generation failed for primary key: {bundle.primary_key_value}",
                    traceback.format_exc(),
                )
                self._create_failed_document_record(task_id, requirements, bundle)
                continue

        status = _final_status(success_count, failed_count)
        completed_at = _utc_now()
        error_message = "" if failed_count == 0 else f"{failed_count} document(s) failed."
        self._update_task_summary(
            task_id,
            status=status,
            total_rows=len(bundles),
            success_count=success_count,
            failed_count=failed_count,
            error_message=error_message,
            completed_at=completed_at,
        )
        self._update_meta(task_id, status, document_ids, len(bundles), success_count, failed_count, completed_at)
        self._log(task_id, "", "info", "complete", f"Generation finished with status: {status.value}.")

        return GenerateTaskResult(
            task_id=task_id,
            status=status,
            total_rows=len(bundles),
            success_count=success_count,
            failed_count=failed_count,
            document_ids=document_ids,
            error_message=error_message,
        )

    def _generate_one_document(
        self,
        *,
        task_id: str,
        requirements: TemplateRequirements,
        template_path: Path,
        bundle: ReportContextBundle,
        ai_enabled: bool,
    ) -> DocumentRecord:
        workspace = create_task_workspace(task_id, self.settings)
        output_filename = build_safe_output_filename(requirements.template_name, bundle.primary_key_value)
        output_path = workspace.output_dir / output_filename
        rendered_path = workspace.temp_dir / f"{bundle.doc_id}.rendered.docx"

        render_result = self.dependencies.render_docx_template(template_path, bundle.context, rendered_path)
        if not render_result.success:
            raise RuntimeError(render_result.error_message)

        ai_results = self._generate_ai_results(template_path, bundle.context, ai_enabled)
        final_result = self.dependencies.finalize_docx(rendered_path, output_path, ai_results, ai_enabled)
        if final_result.error_message:
            raise RuntimeError(final_result.error_message)

        trace_preview_result = self.dependencies.build_trace_and_preview(
            BuildTracePreviewInput(
                task_id=task_id,
                doc_id=bundle.doc_id,
                template_id=requirements.template_id,
                template_name=requirements.template_name,
                template_file=requirements.template_file,
                output_file=output_filename,
                output_path=output_path,
                main_table=requirements.main_table,
                main_table_cn=_main_table_cn(requirements),
                primary_key_field=requirements.primary_key_field,
                primary_key_value=bundle.primary_key_value,
                trace_map=bundle.trace_map,
                ai_blocks=final_result.ai_blocks,
                final_docx_path=output_path,
                template_path=template_path,
            )
        )
        _remove_if_exists(rendered_path)

        now = _utc_now()
        record = DocumentRecord(
            doc_id=bundle.doc_id,
            task_id=task_id,
            template_id=requirements.template_id,
            template_name=requirements.template_name,
            primary_key_value=bundle.primary_key_value,
            output_filename=output_filename,
            output_path=_relative_path(output_path, self.settings.project_root),
            trace_filename=trace_preview_result.trace_file_path.name,
            trace_path=_relative_path(trace_preview_result.trace_file_path, self.settings.project_root),
            preview_filename=trace_preview_result.preview_file_path.name,
            preview_path=_relative_path(trace_preview_result.preview_file_path, self.settings.project_root),
            status=_document_status(final_result.ai_status),
            ai_status=AIStatus(final_result.ai_status),
            trace_count=trace_preview_result.trace_count,
            ai_block_count=trace_preview_result.ai_block_count,
            created_at=now,
            updated_at=now,
        )
        return self.document_repository.create(record)

    def _generate_ai_results(
        self,
        template_path: Path,
        context: dict[str, Any],
        ai_enabled: bool,
    ) -> list[AIGenerateResult]:
        if not ai_enabled:
            return []

        results: list[AIGenerateResult] = []
        for prompt in self.dependencies.load_ai_prompts_from_template(template_path):
            results.append(
                self.dependencies.generate_ai_text(
                    AIGenerateInput(
                        block_id=prompt.block_id,
                        prompt_template=prompt.prompt_template,
                        context=context,
                        model=self.settings.deepseek_model,
                    ),
                    settings=self.settings,
                )
            )
        return results

    def _create_failed_document_record(
        self,
        task_id: str,
        requirements: TemplateRequirements,
        bundle: ReportContextBundle,
    ) -> None:
        now = _utc_now()
        output_filename = build_safe_output_filename(requirements.template_name, bundle.primary_key_value)
        output_path = create_task_workspace(task_id, self.settings).output_dir / output_filename
        record = DocumentRecord(
            doc_id=bundle.doc_id,
            task_id=task_id,
            template_id=requirements.template_id,
            template_name=requirements.template_name,
            primary_key_value=bundle.primary_key_value,
            output_filename=output_filename,
            output_path=_relative_path(output_path, self.settings.project_root),
            trace_filename="",
            trace_path="",
            preview_filename="",
            preview_path="",
            status=DocumentStatus.FAILED,
            ai_status=AIStatus.FAILED,
            error_message="Document generation failed.",
            created_at=now,
            updated_at=now,
        )
        self.document_repository.create(record)

    def _update_task_running(self, task_id: str, started_at: datetime) -> None:
        self.connection.execute(
            """
            UPDATE tasks
            SET status = ?, started_at = ?, updated_at = ?, error_message = ''
            WHERE task_id = ?
            """,
            (TaskStatus.RUNNING.value, started_at.isoformat(), started_at.isoformat(), task_id),
        )

    def _update_task_summary(
        self,
        task_id: str,
        *,
        status: TaskStatus,
        total_rows: int,
        success_count: int,
        failed_count: int,
        error_message: str,
        completed_at: datetime,
    ) -> None:
        self.connection.execute(
            """
            UPDATE tasks
            SET status = ?, total_rows = ?, success_count = ?, failed_count = ?,
                error_message = ?, completed_at = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (
                status.value,
                total_rows,
                success_count,
                failed_count,
                error_message,
                completed_at.isoformat(),
                completed_at.isoformat(),
                task_id,
            ),
        )

    def _update_meta(
        self,
        task_id: str,
        status: TaskStatus,
        document_ids: list[str],
        total_rows: int,
        success_count: int,
        failed_count: int,
        completed_at: datetime,
    ) -> None:
        workspace = create_task_workspace(task_id, self.settings)
        if not workspace.meta_path.exists():
            return

        meta = TaskMeta.model_validate_json(workspace.meta_path.read_text(encoding="utf-8"))
        meta = meta.model_copy(
            update={
                "status": status,
                "updated_at": completed_at,
                "completed_at": completed_at,
                "output_summary": OutputSummary(
                    total_rows=total_rows,
                    success_count=success_count,
                    failed_count=failed_count,
                    document_ids=document_ids,
                ),
            }
        )
        workspace.meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    def _log(
        self,
        task_id: str,
        doc_id: str,
        level: str,
        stage: str,
        message: str,
        detail: str = "",
    ) -> None:
        created_at = _utc_now()
        self.connection.execute(
            """
            INSERT INTO generation_logs (task_id, doc_id, level, stage, message, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, doc_id, level, stage, message, detail, created_at.isoformat()),
        )
        workspace = create_task_workspace(task_id, self.settings)
        line = f"{created_at.isoformat()} [{level.upper()}] {stage} {doc_id} {message}"
        if detail:
            line = f"{line}\n{detail}"
        workspace.logs_dir.mkdir(parents=True, exist_ok=True)
        with (workspace.logs_dir / "generation.log").open("a", encoding="utf-8") as log_file:
            log_file.write(f"{line}\n")


def _assert_can_generate(status: TaskStatus | str, force: bool) -> None:
    status_value = status.value if isinstance(status, TaskStatus) else status
    allowed = {TaskStatus.UPLOADED.value, TaskStatus.VALIDATED.value, TaskStatus.VALIDATION_FAILED.value}
    if force:
        allowed.update({TaskStatus.COMPLETED.value, TaskStatus.PARTIAL_FAILED.value, TaskStatus.FAILED.value})
    if status_value not in allowed:
        raise AppError(
            code="TASK_STATUS_INVALID",
            message=f"Task status cannot generate: {status}",
            status_code=409,
            details={"status": status},
        )


def _final_status(success_count: int, failed_count: int) -> TaskStatus:
    if success_count > 0 and failed_count == 0:
        return TaskStatus.COMPLETED
    if success_count > 0 and failed_count > 0:
        return TaskStatus.PARTIAL_FAILED
    return TaskStatus.FAILED


def _document_status(ai_status: str) -> DocumentStatus:
    if ai_status == AIStatus.PARTIAL_FAILED.value:
        return DocumentStatus.AI_PARTIAL_FAILED
    return DocumentStatus.SUCCESS


def _main_table_cn(requirements: TemplateRequirements) -> str:
    for table in requirements.required_tables:
        if table.table_name == requirements.main_table:
            return table.table_name_cn
    return ""


def _resolve_project_path(path_value: str, project_root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = project_root / path
    return path


def _relative_path(path: Path, project_root: Path) -> str:
    return Path(path).resolve().relative_to(project_root.resolve()).as_posix()


def _remove_if_exists(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
