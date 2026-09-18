"""
Provider abstraction for Hermes Legal Advisor.

Every provider (Groq, Gemini, OpenRouter, Ollama, or the offline rule
engine) implements the same tiny interface: given a contract's text and
some context, return a structured analysis dict. This keeps the rest of
the codebase completely unaware of which backend is actually doing the
thinking.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


ANALYSIS_SCHEMA_HINT = """
Respond with ONLY a single JSON object (no markdown fences, no commentary)
matching this exact shape:

{
  "contract_type": "string",
  "parties": "string describing the parties",
  "language": "EN or TR",
  "clauses": [
    {
      "name": "string, e.g. Termination",
      "score": 1-10,
      "is_red_flag": true/false,
      "finding": "one or two sentence explanation",
      "negotiation_suggestion": "concrete replacement language, or empty string"
    }
  ],
  "missing_clauses": ["string", ...],
  "key_terms": {"Payment": "string", "Term": "string", "...": "..."},
  "overall_risk": "CRITICAL|HIGH|MEDIUM|LOW",
  "verdict": "SIGN|NEGOTIATE|REJECT",
  "summary": "2-4 sentence executive summary",
  "recommendations": ["string", ...]
}

Score every clause on a 1-10 scale where 10 is the worst possible outcome
for the party whose perspective you were given. Always include at least
these clause categories when present in the contract: Termination,
Liability, Intellectual Property, Confidentiality, Non-Compete, Payment
Terms, Auto-Renewal, Dispute Resolution, Governing Law.
"""


@dataclass
class AnalysisResult:
    """Normalized output of any provider, regardless of backend."""

    contract_type: str = "Unknown"
    parties: str = "Unknown"
    language: str = "EN"
    clauses: List[Dict[str, Any]] = field(default_factory=list)
    missing_clauses: List[str] = field(default_factory=list)
    key_terms: Dict[str, str] = field(default_factory=dict)
    overall_risk: str = "MEDIUM"
    verdict: str = "NEGOTIATE"
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    provider: str = "unknown"
    raw: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "parties": self.parties,
            "language": self.language,
            "clauses": self.clauses,
            "missing_clauses": self.missing_clauses,
            "key_terms": self.key_terms,
            "overall_risk": self.overall_risk,
            "verdict": self.verdict,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "provider": self.provider,
        }


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete an analysis."""


class BaseProvider(ABC):
    """Common interface every backend must implement."""

    name = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider has what it needs to run (key, binary, etc.)."""

    @abstractmethod
    def analyze(
        self,
        contract_text: str,
        perspective: str = "neutral",
        language_hint: Optional[str] = None,
        memory_context: str = "",
    ) -> AnalysisResult:
        """Run a full analysis and return a normalized AnalysisResult."""

    def build_prompt(
        self,
        contract_text: str,
        perspective: str,
        memory_context: str,
    ) -> str:
        perspective_line = (
            f"You are analyzing this contract strictly from the perspective of "
            f"the {perspective}. Score risk based on how this contract affects "
            f"that party specifically."
            if perspective and perspective != "neutral"
            else "Analyze this contract from a neutral, balanced perspective."
        )
        return (
            "You are Hermes Legal Advisor, a meticulous contract analyst. "
            "You are not a lawyer and always recommend consulting one before "
            "signing anything. " + perspective_line + "\n\n"
            + (f"Context from previously analyzed contracts:\n{memory_context}\n\n" if memory_context else "")
            + "Contract text:\n\"\"\"\n" + contract_text[:12000] + "\n\"\"\"\n\n"
            + ANALYSIS_SCHEMA_HINT
        )

    @staticmethod
    def parse_json_response(text: str) -> Dict[str, Any]:
        """Best-effort extraction of a JSON object from a model response."""
        text = text.strip()
        # Strip markdown code fences if the model added them anyway.
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fall back to grabbing the first {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise ProviderError(f"Could not parse model response as JSON: {exc}") from exc
        raise ProviderError("Model response did not contain a JSON object.")

    @classmethod
    def result_from_json(cls, data: Dict[str, Any], provider_name: str, raw: str = "") -> AnalysisResult:
        return AnalysisResult(
            contract_type=str(data.get("contract_type", "Unknown")),
            parties=str(data.get("parties", "Unknown")),
            language=str(data.get("language", "EN")).upper()[:2] or "EN",
            clauses=list(data.get("clauses", []) or []),
            missing_clauses=list(data.get("missing_clauses", []) or []),
            key_terms=dict(data.get("key_terms", {}) or {}),
            overall_risk=str(data.get("overall_risk", "MEDIUM")).upper(),
            verdict=str(data.get("verdict", "NEGOTIATE")).upper(),
            summary=str(data.get("summary", "")),
            recommendations=list(data.get("recommendations", []) or []),
            provider=provider_name,
            raw=raw,
        )
