"""OpenRouter provider - keeps access to OpenRouter's free-tier models
(e.g. many :free suffixed models) and any paid model the user chooses."""

from __future__ import annotations

import os
from typing import Optional

from .base import AnalysisResult, BaseProvider, ProviderError

DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_OPENROUTER_MODEL):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.model = model

    def is_available(self) -> bool:
        return bool(self.api_key)

    def analyze(
        self,
        contract_text: str,
        perspective: str = "neutral",
        language_hint: Optional[str] = None,
        memory_context: str = "",
    ) -> AnalysisResult:
        if not self.api_key:
            raise ProviderError(
                "OPENROUTER_API_KEY is not set. Create one at https://openrouter.ai/keys "
                "(many models on OpenRouter, including the default here, are free)."
            )

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("The 'openai' package is required. Install with: pip install openai") from exc

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/Lethe044/hermes-legal",
                "X-Title": "Hermes Legal Advisor",
            },
        )
        prompt = self.build_prompt(contract_text, perspective, memory_context)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You output only valid JSON, nothing else."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content or ""
        data = self.parse_json_response(raw)
        return self.result_from_json(data, self.name, raw)
