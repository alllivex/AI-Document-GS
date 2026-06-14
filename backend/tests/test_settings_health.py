from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings


def test_settings_health_returns_unified_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/settings/health")

    payload = response.json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["data"] == {"status": "ok"}
    assert payload["request_id"]
    assert payload["timestamp"]
