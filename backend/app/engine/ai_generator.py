from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.engine.ai_client import DeepSeekClient
from app.services.ai_config_service import resolve_ai_config


class AIGenerateInput(BaseModel):
    block_id: str
    prompt_template: str
    context: dict[str, Any]
    model: str = "deepseek-chat"


class AIGenerateResult(BaseModel):
    block_id: str
    status: Literal["success", "failed"]
    prompt_template: str
    prompt_rendered: str
    generated_text: str
    model: str
    error_message: str
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AITextClient(Protocol):
    def generate(self, prompt: str, model: str | None = None) -> str:
        ...


def render_prompt(prompt_tpl: str, context: dict[str, Any]) -> str:
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    return environment.from_string(prompt_tpl).render(context)


def generate_ai_text(
    input_data: AIGenerateInput,
    *,
    client: AITextClient | None = None,
    settings: AppSettings | None = None,
) -> AIGenerateResult:
    started_at = datetime.now(timezone.utc)
    prompt_rendered = ""

    try:
        prompt_rendered = render_prompt(input_data.prompt_template, input_data.context)
    except Exception as exc:
        return _failed(input_data, prompt_rendered, started_at, f"Failed to render AI prompt: {exc}")

    try:
        active_client, active_model = _build_client_with_model(client, settings, input_data.model)
    except ValueError as exc:
        return _failed(input_data, prompt_rendered, started_at, f"AI unavailable: {exc}")

    try:
        generated_text = active_client.generate(prompt_rendered, model=active_model)
    except Exception as exc:
        return _failed(input_data, prompt_rendered, started_at, f"AI generation failed: {exc}")

    return AIGenerateResult(
        block_id=input_data.block_id,
        status="success",
        prompt_template=input_data.prompt_template,
        prompt_rendered=prompt_rendered,
        generated_text=generated_text,
        model=active_model or input_data.model,
        error_message="",
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )


def _build_client_with_model(
    client: AITextClient | None,
    settings: AppSettings | None,
    fallback_model: str,
) -> tuple[AITextClient, str | None]:
    if client is not None:
        return client, fallback_model

    config = resolve_ai_config(settings or get_settings())
    if not config.api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")
    if not config.is_active:
        raise ValueError("AI config is not active")
    return (
        DeepSeekClient(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
        ),
        config.model_name,
    )


def _failed(
    input_data: AIGenerateInput,
    prompt_rendered: str,
    started_at: datetime,
    error_message: str,
) -> AIGenerateResult:
    return AIGenerateResult(
        block_id=input_data.block_id,
        status="failed",
        prompt_template=input_data.prompt_template,
        prompt_rendered=prompt_rendered,
        generated_text="",
        model=input_data.model,
        error_message=error_message,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )
