from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import AppSettings, get_settings
from app.core.errors import AppError
from app.db.repositories.ai_config_repository import AIConfigRepository
from app.engine.ai_client import DeepSeekClient
from app.models.settings_models import AIConfigResponse, AIConfigTestResult, AIConfigUpdateRequest

DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class ResolvedAIConfig:
    provider: str
    model_name: str
    base_url: str
    temperature: float
    timeout_seconds: int
    api_key: str | None
    api_key_source: str
    is_active: bool

    @property
    def api_key_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def status(self) -> str:
        return "available" if self.is_active and self.api_key_configured else "unavailable"


class AIConfigService:
    def __init__(self, repository: AIConfigRepository, settings: AppSettings | None = None) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    def get_config(self) -> AIConfigResponse:
        return self._to_response(self.resolve_config())

    def update_config(self, payload: AIConfigUpdateRequest) -> AIConfigResponse:
        provider = payload.provider.strip() or DEFAULT_PROVIDER
        model_name = payload.model_name.strip() or DEFAULT_MODEL
        base_url = payload.base_url.strip() or DEFAULT_BASE_URL
        if provider != DEFAULT_PROVIDER:
            raise AppError("BAD_REQUEST", "MVP 仅支持 provider=deepseek", 400)
        api_key_source = "env" if self.settings.deepseek_api_key else "none"
        self.repository.upsert_active(
            provider=provider,
            model_name=model_name,
            base_url=base_url,
            temperature=payload.temperature,
            timeout_seconds=payload.timeout_seconds,
            api_key_source=api_key_source,
            is_active=payload.is_active,
            now=self._now(),
        )
        return self.get_config()

    def test_connection(self) -> AIConfigTestResult:
        config = self.resolve_config()
        if not config.api_key:
            return AIConfigTestResult(status="failed", message="API Key未配置")
        if not config.is_active:
            return AIConfigTestResult(status="failed", message="AI配置未启用")
        try:
            client = DeepSeekClient(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model_name,
                temperature=config.temperature,
                timeout_seconds=config.timeout_seconds,
            )
            client.generate("请回复：ok", model=config.model_name)
        except Exception as exc:
            return AIConfigTestResult(status="failed", message=f"AI连接测试失败：{self._safe_error(exc)}")
        return AIConfigTestResult(status="success", message="AI连接测试成功")

    def resolve_config(self) -> ResolvedAIConfig:
        row = self.repository.get_active()
        api_key = self.settings.deepseek_api_key
        api_key_source = "env" if api_key else "none"
        if row:
            return ResolvedAIConfig(
                provider=row["provider"],
                model_name=row["model_name"],
                base_url=row["base_url"],
                temperature=float(row["temperature"]),
                timeout_seconds=int(row["timeout_seconds"]),
                api_key=api_key,
                api_key_source=api_key_source,
                is_active=bool(row["is_active"]),
            )
        return ResolvedAIConfig(
            provider=DEFAULT_PROVIDER,
            model_name=self.settings.deepseek_model or DEFAULT_MODEL,
            base_url=self.settings.deepseek_base_url or DEFAULT_BASE_URL,
            temperature=self.settings.deepseek_temperature,
            timeout_seconds=self.settings.deepseek_timeout_seconds,
            api_key=api_key,
            api_key_source=api_key_source,
            is_active=True,
        )

    def _to_response(self, config: ResolvedAIConfig) -> AIConfigResponse:
        return AIConfigResponse(
            provider=config.provider,
            model_name=config.model_name,
            base_url=config.base_url,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            api_key_configured=config.api_key_configured,
            api_key_source=config.api_key_source,
            is_active=config.is_active,
            status=config.status,
        )

    def _safe_error(self, exc: Exception) -> str:
        message = str(exc)
        api_key = self.settings.deepseek_api_key
        if api_key:
            message = message.replace(api_key, "***")
        return message

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()


def resolve_ai_config(settings: AppSettings | None = None) -> ResolvedAIConfig:
    from app.db.connection import get_connection

    with get_connection() as connection:
        return AIConfigService(AIConfigRepository(connection), settings or get_settings()).resolve_config()
