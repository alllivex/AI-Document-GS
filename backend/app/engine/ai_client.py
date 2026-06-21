from __future__ import annotations

import certifi
import httpx
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
WORD_READY_SYSTEM_PROMPT = (
    "You are a precise business document writing assistant. "
    "Do not use Markdown formatting. Do not output headings like ###, bullet markers like * or -, "
    "or table syntax. Write natural paragraphs suitable for the body of a Word business report. "
    "For causes that cannot be directly proven by the provided data, use cautious wording such as "
    "'may' or 'requires further verification'. Do not invent customers, industries, regions, approvals, "
    "asset-quality causes, or facts that were not provided. Prefer two paragraphs: first risk analysis, "
    "then management suggestions."
)


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        model: str = DEFAULT_DEEPSEEK_MODEL,
        temperature: float = 0.2,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured")
        self.model = model
        self.temperature = temperature

        # Build a custom httpx Client that uses certifi's CA bundle directly,
        # ignoring the SSL_CERT_FILE / SSL_CERT_DIR environment variables.
        # This prevents "FileNotFoundError" crashes when SSL_CERT_FILE
        # is set to a non-existent path (e.g. from Anaconda activation scripts).
        ssl_context = httpx.create_ssl_context(verify=certifi.where(), trust_env=False)
        http_client = httpx.Client(verify=ssl_context, timeout=timeout_seconds)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            timeout=timeout_seconds,
        )

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
                {"role": "system", "content": WORD_READY_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
        )
        return (response.choices[0].message.content or "").strip()

    def rewrite(self, text_final: str, prompt_final: str, model: str | None = None) -> str:
        prompt = (
            "Please generate final Word-ready body text from the current paragraph and task.\n\n"
            f"Current paragraph:\n{text_final}\n\nTask:\n{prompt_final}"
        )
        return self.generate(prompt, model=model)