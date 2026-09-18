"""Groq provider - free tier, very fast inference on open models."""

from __future__ import annotations

import os
from typing import Optional

from .base import AnalysisResult, BaseProvider, ProviderError

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_GROQ_MODEL):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
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
            raise ProviderError("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys")

        try:
            from groq import Groq
        except ImportError as exc:
            raise ProviderError("The 'groq' package is required. Install with: pip install groq") from exc

        client = Groq(api_key=self.api_key)
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
