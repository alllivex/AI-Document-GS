from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.models.api_models import ApiError, ApiErrorDetail, ApiSuccess
from app.models.enums import DataType, RelationType, TaskStatus, ValidationStatus
from app.models.file_models import SourceFileInfo, UploadedFileMeta
from app.models.preview_models import PreviewFile
from app.models.task_models import OutputSummary, TaskMeta, TaskPaths
from app.models.template_models import RequiredTable
from app.models.trace_models import TraceFile, TraceItem, TraceStatistics
from app.models.validation_models import ValidationItem, ValidationReport, ValidationSummary

NOW = datetime(2026, 6, 13, 15, 30, tzinfo=timezone.utc)


def make_trace_item() -> TraceItem:
    return TraceItem(
        trace_id="trace_550e8400-e29b-41d4-a716-446655440001",
        var_path="customer_info.customer_name",
        table_name="customer_info",
        table_name_cn="客户信息表",
        field_name="customer_name",
        field_name_cn="客户名称",
        source_file="customer_info.xlsx",
        source_file_path="tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
        pk_field="customer_id",
        pk_value="C001",
        row_index=0,
        excel_row_number=2,
        column_index=1,
        excel_column_letter="B",
        raw_value="张三公司",
        display_value="张三公司",
        value_type=DataType.STRING,
        display_format="",
        occurrence_index=0,
        source_relation_type=RelationType.MAIN,
        created_at=NOW,
    )


def test_trace_item_validates_contract_fields() -> None:
    item = make_trace_item()

    assert item.value_type == "string"
    assert item.source_relation_type == "main"
    assert "data." not in item.var_path


def test_invalid_enum_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TraceItem(**{**make_trace_item().model_dump(), "value_type": "currency"})


def test_trace_file_validates_nested_models() -> None:
    trace_file = TraceFile(
        doc_id="doc_550e8400-e29b-41d4-a716-446655440000",
        task_id="task_20260613_153000_a1b2c3",
        template_id=1,
        template_name="客户尽调报告",
        template_file="due_diligence.docx",
        output_file="客户尽调报告_C001.docx",
        output_path="tasks/task_20260613_153000_a1b2c3/output/客户尽调报告_C001.docx",
        main_table="customer_info",
        main_table_cn="客户信息表",
        primary_key_field="customer_id",
        primary_key_value="C001",
        generated_at=NOW,
        source_files=[
            SourceFileInfo(
                table_name="customer_info",
                table_name_cn="客户信息表",
                filename="customer_info.xlsx",
                path="tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
                row_count=3,
                column_count=8,
            )
        ],
        trace_items=[make_trace_item()],
        ai_blocks=[],
        statistics=TraceStatistics(
            trace_item_count=1,
            ai_block_count=0,
            source_file_count=1,
            table_count=1,
        ),
    )

    assert trace_file.schema_version == "1.0"
    assert trace_file.trace_items[0].trace_id.startswith("trace_")


def test_preview_file_discriminates_block_types() -> None:
    preview = PreviewFile(
        doc_id="doc_550e8400-e29b-41d4-a716-446655440000",
        task_id="task_20260613_153000_a1b2c3",
        title="客户尽调报告_C001.docx",
        output_file="客户尽调报告_C001.docx",
        primary_key_value="C001",
        blocks=[
            {"type": "heading", "block_id": "block_001", "level": 1, "text": "客户尽调报告"},
            {
                "type": "paragraph",
                "block_id": "block_002",
                "runs": [{"text": "张三公司", "trace_id": "trace_550e8400-e29b-41d4-a716-446655440001"}],
            },
        ],
        created_at=NOW,
    )

    assert preview.blocks[0].type == "heading"
    assert preview.blocks[1].type == "paragraph"


def test_validation_report_rejects_invalid_status() -> None:
    report = ValidationReport(
        task_id="task_20260613_153000_a1b2c3",
        status=ValidationStatus.FAILED,
        summary=ValidationSummary(error_count=1, warning_count=0, info_count=0),
        items=[
            ValidationItem(
                level="error",
                code="missing_field",
                message="缺少字段。",
                table_name="loan_summary",
                field_name="loan_balance",
            )
        ],
        created_at=NOW,
    )

    assert report.status == "failed"

    with pytest.raises(ValidationError):
        ValidationReport(
            task_id="task_20260613_153000_a1b2c3",
            status="ok",
            summary=ValidationSummary(),
            items=[],
            created_at=NOW,
        )


def test_task_meta_validates_nested_task_metadata() -> None:
    meta = TaskMeta(
        task_id="task_20260613_153000_a1b2c3",
        task_name="客户尽调报告批量生成",
        template_id=1,
        template_name="客户尽调报告",
        template_file="due_diligence.docx",
        ai_enabled=True,
        status=TaskStatus.CREATED,
        main_table="customer_info",
        main_table_cn="客户信息表",
        primary_key_field="customer_id",
        required_tables=[
            RequiredTable(
                table_name="customer_info",
                table_name_cn="客户信息表",
                role="main",
                relation_type="main",
                required=True,
            )
        ],
        uploaded_files=[
            UploadedFileMeta(
                table_name="customer_info",
                original_filename="客户信息表.xlsx",
                stored_filename="customer_info.xlsx",
                path="tasks/task_20260613_153000_a1b2c3/data/customer_info.xlsx",
                row_count=3,
                column_count=8,
                uploaded_at=NOW,
            )
        ],
        output_summary=OutputSummary(),
        paths=TaskPaths(
            task_dir="tasks/task_20260613_153000_a1b2c3",
            data_dir="tasks/task_20260613_153000_a1b2c3/data",
            output_dir="tasks/task_20260613_153000_a1b2c3/output",
            validation_dir="tasks/task_20260613_153000_a1b2c3/validation",
            logs_dir="tasks/task_20260613_153000_a1b2c3/logs",
        ),
        created_at=NOW,
        updated_at=NOW,
    )

    assert meta.schema_version == "1.0"
    assert meta.required_tables[0].role == "main"


def test_api_response_models_validate_success_and_error_shapes() -> None:
    success = ApiSuccess[dict[str, str]](
        data={"status": "ok"},
        request_id="req_550e8400-e29b-41d4-a716-446655440999",
        timestamp=NOW,
    )
    error = ApiError(
        error=ApiErrorDetail(
            code="TASK_NOT_FOUND",
            message="任务不存在。",
            detail={"task_id": "task_20260613_153000_a1b2c3"},
        ),
        request_id="req_550e8400-e29b-41d4-a716-446655440999",
        timestamp=NOW,
    )

    assert success.success is True
    assert success.data == {"status": "ok"}
    assert error.success is False
    assert error.error.code == "TASK_NOT_FOUND"
