import os
from pathlib import Path
from typing import Protocol, TypeVar
from pydantic import BaseModel
from openai import OpenAI

T = TypeVar("T", bound=BaseModel)
PROMPTS = Path(__file__).resolve().parents[1] / "prompts"


class LLMProvider(Protocol):
    def structured_generate(self, prompt: str, data: str, schema: type[T]) -> tuple[T, dict]: ...


class OpenAIProvider:
    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("Live mode requires OPENAI_API_KEY on the backend")
        self.client = OpenAI(timeout=30, max_retries=1)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def structured_generate(self, prompt, data, schema):
        response = self.client.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": data}],
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Provider refused or returned no structured output")
        u = response.usage
        return parsed, {
            "prompt_tokens": u.prompt_tokens if u else None,
            "completion_tokens": u.completion_tokens if u else None,
            "total_tokens": u.total_tokens if u else None,
            "source": "provider" if u else "unavailable",
        }


def cost(usage, mode):
    if mode == "demo":
        return 0.0
    a, b = os.getenv("INPUT_USD_PER_MILLION"), os.getenv("OUTPUT_USD_PER_MILLION")
    if not a or not b or usage.get("prompt_tokens") is None or usage.get("source") == "unavailable":
        return None
    return (usage["prompt_tokens"] * float(a) + usage["completion_tokens"] * float(b)) / 1_000_000
