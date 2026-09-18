"""Ollama provider - fully local, fully free, no API key, no internet
required once the model is pulled. Good for privileged/confidential
contracts that should never leave the machine."""

from __future__ import annotations

import json
import os
from typing import Optional

from .base import AnalysisResult, BaseProvider, ProviderError

DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, model: str = DEFAULT_OLLAMA_MODEL, host: Optional[str] = None):
        self.model = model
        self.host = host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

    def is_available(self) -> bool:
        try:
            import urllib.request

            urllib.request.urlopen(f"{self.host}/api/tags", timeout=1.5)
            return True
        except Exception:
            return False

    def analyze(
        self,
        contract_text: str,
        perspective: str = "neutral",
        language_hint: Optional[str] = None,
        memory_context: str = "",
    ) -> AnalysisResult:
        import urllib.error
        import urllib.request

        prompt = self.build_prompt(contract_text, perspective, memory_context)
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderError(
                f"Could not reach Ollama at {self.host}. Is `ollama serve` running "
                f"and did you `ollama pull {self.model}`?"
            ) from exc

        raw = body.get("response", "")
        data = self.parse_json_response(raw)
        return self.result_from_json(data, self.name, raw)
