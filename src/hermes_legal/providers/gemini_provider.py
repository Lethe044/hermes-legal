"""Google Gemini provider - generous free tier via Google AI Studio."""

from __future__ import annotations

import os
from typing import Optional

from .base import AnalysisResult, BaseProvider, ProviderError

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
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
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey"
            )

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError(
                "The 'google-generativeai' package is required. "
                "Install with: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=self.api_key)
        prompt = self.build_prompt(contract_text, perspective, memory_context)

        model = genai.GenerativeModel(
            self.model,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"},
        )
        response = model.generate_content(prompt)
        raw = response.text or ""
        data = self.parse_json_response(raw)
        return self.result_from_json(data, self.name, raw)
