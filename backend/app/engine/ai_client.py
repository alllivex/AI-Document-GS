from __future__ import annotations

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        model: str = DEFAULT_DEEPSEEK_MODEL,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def generate(self, prompt: str, model: str | None = None) -> str:
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": "You are a precise business document writing assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return (response.choices[0].message.content or "").strip()

    def rewrite(self, text_final: str, prompt_final: str, model: str | None = None) -> str:
        prompt = (
            "Please generate final Word-ready body text from the current paragraph and task.\n\n"
            f"Current paragraph:\n{text_final}\n\nTask:\n{prompt_final}"
        )
        return self.generate(prompt, model=model)
