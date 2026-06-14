from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import AppSettings
from app.engine.ai_generator import AIGenerateInput, generate_ai_text, render_prompt


class MockAIClient:
    def __init__(self, response: str = "generated text", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    def generate(self, prompt: str, model: str | None = None) -> str:
        self.calls.append((prompt, model))
        if self.error is not None:
            raise self.error
        return self.response


def settings_without_api_key(tmp_path: Path) -> AppSettings:
    return AppSettings(
        project_root=tmp_path,
        database_path=tmp_path / "config" / "db.sqlite",
        config_dir=tmp_path / "config",
        templates_dir=tmp_path / "templates",
        tasks_dir=tmp_path / "tasks",
        temp_dir=tmp_path / "temp",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com/v1",
        deepseek_model="deepseek-chat",
    )


def make_input() -> AIGenerateInput:
    return AIGenerateInput(
        block_id="AIBLOCK0",
        prompt_template="Analyze {{ customer_info.customer_name }} with balance {{ loan_summary.loan_balance }}.",
        context={
            "customer_info": {"customer_name": "Acme"},
            "loan_summary": {"loan_balance": "1200.00"},
        },
    )


def test_render_prompt_uses_jinja2_variables() -> None:
    rendered = render_prompt(
        "Hello {{ customer_info.customer_name }}",
        {"customer_info": {"customer_name": "Acme"}},
    )

    assert rendered == "Hello Acme"


def test_generate_ai_text_returns_ai_unavailable_when_api_key_missing(tmp_path) -> None:
    result = generate_ai_text(make_input(), settings=settings_without_api_key(tmp_path))

    assert result.status == "failed"
    assert result.generated_text == ""
    assert result.prompt_rendered == "Analyze Acme with balance 1200.00."
    assert "AI unavailable" in result.error_message
    assert "DEEPSEEK_API_KEY" in result.error_message
    assert result.started_at is not None
    assert result.completed_at is not None


def test_generate_ai_text_uses_mock_client_without_real_deepseek_call() -> None:
    client = MockAIClient(response="Acme risk is controlled.")

    result = generate_ai_text(make_input(), client=client)

    assert result.status == "success"
    assert result.generated_text == "Acme risk is controlled."
    assert result.error_message == ""
    assert client.calls == [("Analyze Acme with balance 1200.00.", "deepseek-chat")]


def test_generate_ai_text_returns_failed_when_ai_call_raises() -> None:
    client = MockAIClient(error=RuntimeError("network boom"))

    result = generate_ai_text(make_input(), client=client)

    assert result.status == "failed"
    assert result.generated_text == ""
    assert "AI generation failed" in result.error_message
    assert "network boom" in result.error_message


def test_generate_ai_text_returns_failed_when_prompt_rendering_fails() -> None:
    result = generate_ai_text(
        AIGenerateInput(
            block_id="AIBLOCK0",
            prompt_template="Hello {{ missing.value }}",
            context={},
        ),
        client=MockAIClient(),
    )

    assert result.status == "failed"
    assert result.prompt_rendered == ""
    assert "Failed to render AI prompt" in result.error_message
