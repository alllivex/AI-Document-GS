from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from app.core.config import AppSettings, get_settings
from app.engine.ai_client import DeepSeekClient


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
        active_client = client or _build_client(settings)
    except ValueError as exc:
        return _failed(input_data, prompt_rendered, started_at, f"AI unavailable: {exc}")

    try:
        generated_text = active_client.generate(prompt_rendered, model=input_data.model)
    except Exception as exc:
        return _failed(input_data, prompt_rendered, started_at, f"AI generation failed: {exc}")

    return AIGenerateResult(
        block_id=input_data.block_id,
        status="success",
        prompt_template=input_data.prompt_template,
        prompt_rendered=prompt_rendered,
        generated_text=generated_text,
        model=input_data.model,
        error_message="",
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )


def _build_client(settings: AppSettings | None) -> DeepSeekClient:
    active_settings = settings or get_settings()
    if not active_settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured")
    return DeepSeekClient(
        api_key=active_settings.deepseek_api_key,
        base_url=active_settings.deepseek_base_url,
        model=active_settings.deepseek_model,
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
