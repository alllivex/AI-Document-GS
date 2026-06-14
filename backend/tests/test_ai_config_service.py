from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.db.connection import get_connection
from app.db.init_db import init_db
from app.db.repositories.ai_config_repository import AIConfigRepository
from app.engine.ai_generator import AIGenerateInput, generate_ai_text
from app.models.settings_models import AIConfigUpdateRequest
from app.services.ai_config_service import AIConfigService


class FakeDeepSeekClient:
    instances = []

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float, timeout_seconds: int) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.calls = []
        FakeDeepSeekClient.instances.append(self)

    def generate(self, prompt: str, model: str | None = None) -> str:
        self.calls.append((prompt, model))
        return "ok"


def reset_settings(tmp_path: Path, monkeypatch, api_key: str | None = None):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'config' / 'db.sqlite').as_posix()}")
    if api_key:
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
    else:
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()
    return get_settings()


def test_ai_config_defaults_without_api_key(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        config = AIConfigService(AIConfigRepository(connection), settings).get_config()

    assert config.provider == "deepseek"
    assert config.model_name == "deepseek-chat"
    assert config.base_url == "https://api.deepseek.com/v1"
    assert config.temperature == 0.2
    assert config.timeout_seconds == 60
    assert config.api_key_configured is False
    assert config.api_key_source == "none"
    assert config.status == "unavailable"


def test_ai_config_uses_env_api_key_source_and_saves_model_params(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch, api_key="sk-secret-value")
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        service = AIConfigService(AIConfigRepository(connection), settings)
        config = service.update_config(
            AIConfigUpdateRequest(
                provider="deepseek",
                model_name="deepseek-reasoner",
                base_url="https://api.deepseek.com/v1",
                temperature=0.4,
                timeout_seconds=30,
                is_active=True,
            )
        )

    assert config.model_name == "deepseek-reasoner"
    assert config.temperature == 0.4
    assert config.timeout_seconds == 30
    assert config.api_key_configured is True
    assert config.api_key_source == "env"
    assert config.status == "available"


def test_ai_config_test_connection_reports_missing_key(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch)
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        result = AIConfigService(AIConfigRepository(connection), settings).test_connection()

    assert result.status == "failed"
    assert result.message == "API Key未配置"


def test_ai_config_can_be_saved_inactive(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch, api_key="sk-secret-value")
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        service = AIConfigService(AIConfigRepository(connection), settings)
        config = service.update_config(
            AIConfigUpdateRequest(
                provider="deepseek",
                model_name="deepseek-chat",
                base_url="https://api.deepseek.com/v1",
                temperature=0.2,
                timeout_seconds=60,
                is_active=False,
            )
        )

    assert config.is_active is False
    assert config.api_key_configured is True
    assert config.status == "unavailable"


def test_ai_generator_uses_saved_db_config(tmp_path, monkeypatch) -> None:
    settings = reset_settings(tmp_path, monkeypatch, api_key="sk-secret-value")
    init_db(settings.database_path)
    with get_connection(settings.database_path) as connection:
        AIConfigService(AIConfigRepository(connection), settings).update_config(
            AIConfigUpdateRequest(
                provider="deepseek",
                model_name="deepseek-reasoner",
                base_url="https://example.invalid/v1",
                temperature=0.5,
                timeout_seconds=22,
                is_active=True,
            )
        )

    FakeDeepSeekClient.instances = []
    monkeypatch.setattr("app.engine.ai_generator.DeepSeekClient", FakeDeepSeekClient)
    result = generate_ai_text(
        AIGenerateInput(block_id="AIBLOCK0", prompt_template="Hello {{ name }}", context={"name": "Acme"}),
        settings=settings,
    )

    assert result.status == "success"
    assert result.model == "deepseek-reasoner"
    instance = FakeDeepSeekClient.instances[0]
    assert instance.api_key == "sk-secret-value"
    assert instance.base_url == "https://example.invalid/v1"
    assert instance.temperature == 0.5
    assert instance.timeout_seconds == 22
    assert instance.calls == [("Hello Acme", "deepseek-reasoner")]
