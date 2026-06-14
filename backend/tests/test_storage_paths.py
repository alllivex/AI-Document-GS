from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.storage.file_manager import save_uploaded_file
from app.storage.paths import create_task_workspace, get_upload_file_path
from app.storage.safe_filename import build_safe_output_filename, sanitize_filename


def reset_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    get_settings.cache_clear()
    return get_settings()


def test_create_task_workspace_creates_complete_directory_tree(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    task_id = "task_20260613_153000_a1b2c3"

    workspace = create_task_workspace(task_id, settings)

    assert workspace.task_dir == tmp_path / "tasks" / task_id
    assert workspace.meta_path == workspace.task_dir / "meta.json"
    for directory in (
        workspace.task_dir,
        workspace.data_dir,
        workspace.output_dir,
        workspace.validation_dir,
        workspace.logs_dir,
        workspace.temp_dir,
    ):
        assert directory.is_dir()


def test_save_uploaded_file_writes_table_xlsx_under_task_data(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    file_bytes = b"fake xlsx bytes"

    stored = save_uploaded_file(
        task_id="task_20260613_153000_a1b2c3",
        table_name="customer_info",
        file_bytes=file_bytes,
        original_filename="客户信息表.xlsx",
        settings=settings,
    )

    expected_path = tmp_path / "tasks" / "task_20260613_153000_a1b2c3" / "data" / "customer_info.xlsx"
    assert stored.file_path == expected_path
    assert stored.stored_filename == "customer_info.xlsx"
    assert stored.file_size == len(file_bytes)
    assert expected_path.read_bytes() == file_bytes


def test_sanitize_filename_replaces_illegal_characters() -> None:
    assert sanitize_filename('a\\b/c:d*e?f"g<h>i|j k') == "a_b_c_d_e_f_g_h_i_j_k"


def test_path_traversal_is_rejected(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)

    with pytest.raises(ValueError):
        create_task_workspace("../evil", settings)

    with pytest.raises(ValueError):
        get_upload_file_path("task_20260613_153000_a1b2c3", "../evil", settings)

    with pytest.raises(ValueError):
        save_uploaded_file(
            task_id="task_20260613_153000_a1b2c3",
            table_name="../evil",
            file_bytes=b"bad",
            original_filename="../evil.xlsx",
            settings=settings,
        )

    assert not (tmp_path / "evil.xlsx").exists()


def test_output_filename_is_limited_to_120_chars_with_hash() -> None:
    filename = build_safe_output_filename("客户尽调报告" * 20, "C001" * 20)

    assert len(filename) <= 120
    assert filename.endswith(".docx")
    assert "_" in filename.removesuffix(".docx")[-7:]


def test_upload_rejects_absolute_table_name(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)

    with pytest.raises(ValueError):
        save_uploaded_file(
            task_id="task_20260613_153000_a1b2c3",
            table_name=str(tmp_path / "outside"),
            file_bytes=b"bad",
            original_filename="outside.xlsx",
            settings=settings,
        )
