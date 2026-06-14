from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import create_required_directories, get_settings


def test_health_returns_ok(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_create_required_directories(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()

    settings = get_settings()
    create_required_directories(settings)

    assert settings.config_dir == tmp_path / "config"
    assert settings.templates_dir == tmp_path / "templates"
    assert settings.tasks_dir == tmp_path / "tasks"
    assert settings.temp_dir == tmp_path / "temp"
    assert settings.deepseek_api_key is None
    assert settings.ai_available is False

    for directory_name in ("config", "templates", "tasks", "temp"):
        assert (tmp_path / directory_name).is_dir()
