from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.init_db import init_db


def reset_settings(tmp_path: Path, monkeypatch, api_key: str | None = None):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'config' / 'db.sqlite').as_posix()}")
    if api_key:
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()
    return get_settings()


def assert_success(payload: dict) -> None:
    assert payload["success"] is True
    assert payload["request_id"]
    assert payload["timestamp"]


def test_ai_config_get_and_put_do_not_return_api_key(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch, api_key="sk-secret-value")
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        get_response = client.get("/api/settings/ai-config")
        put_response = client.put(
            "/api/settings/ai-config",
            json={
                "provider": "deepseek",
                "model_name": "deepseek-reasoner",
                "base_url": "https://api.deepseek.com/v1",
                "temperature": 0.3,
                "timeout_seconds": 45,
                "is_active": True,
            },
        )

    assert get_response.status_code == 200
    assert_success(get_response.json())
    assert get_response.json()["data"]["api_key_configured"] is True
    assert get_response.json()["data"]["api_key_source"] == "env"
    assert "sk-secret-value" not in get_response.text
    assert put_response.status_code == 200
    payload = put_response.json()
    assert_success(payload)
    assert payload["data"]["model_name"] == "deepseek-reasoner"
    assert payload["data"]["temperature"] == 0.3
    assert "sk-secret-value" not in put_response.text


def test_ai_config_missing_key_status_and_test_result(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)

    from app.main import create_app

    with TestClient(create_app()) as client:
        get_response = client.get("/api/settings/ai-config")
        test_response = client.post("/api/settings/ai-config/test")

    config = get_response.json()["data"]
    assert get_response.status_code == 200
    assert config["api_key_configured"] is False
    assert config["api_key_source"] == "none"
    assert config["status"] == "unavailable"
    assert test_response.status_code == 200
    assert test_response.json()["data"] == {"status": "failed", "message": "API Key未配置"}
