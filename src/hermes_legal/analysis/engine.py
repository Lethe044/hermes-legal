from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from ..deadlines import extract_obligations
from ..explanations import attach_explanations
from ..memory.store import MemoryStore
from ..playbook import Playbook
from ..providers import AUTO_DETECT_ORDER, PROVIDER_REGISTRY, AnalysisResult, BaseProvider, get_provider
from .risk import RISK_RANK


def file_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def _memory_context_for(memory: MemoryStore, text: str, limit: int = 5) -> str:
    """Build a short context blurb from prior contracts to feed the provider."""
    contracts = memory.contracts()
    if not contracts:
        return ""
    recent = contracts[-limit:]
    lines = []
    for c in recent:
        lines.append(
            f"- [{c.get('timestamp', '?')[:10]}] {c.get('contract_type', '?')} "
            f"with {c.get('parties', '?')} -> risk {c.get('risk_level', '?')}, "
            f"verdict {c.get('verdict', '?')}"
        )
    return "\n".join(lines)


def _analyze_with_fallback(
    provider: BaseProvider, text: str, perspective: str, context: str
) -> tuple[AnalysisResult, Optional[str]]:
    """
    Try the given provider first. If it raises, fall back through
    AUTO_DETECT_ORDER (skipping the one that just failed) until one
    succeeds or all are exhausted. Returns (result, fallback_note) where
    fallback_note is None unless a fallback actually happened.
    """
    try:
        return provider.analyze(text, perspective=perspective, memory_context=context), None
    except Exception as first_exc:
        tried = {provider.name}
        for candidate_name in AUTO_DETECT_ORDER:
            if candidate_name in tried:
                continue
            candidate = PROVIDER_REGISTRY[candidate_name]()
            if not candidate.is_available():
                continue
            tried.add(candidate_name)
            try:
                result = candidate.analyze(text, perspective=perspective, memory_context=context)
                note = f"Provider '{provider.name}' failed ({first_exc}); fell back to '{candidate_name}'."
                return result, note
            except Exception:
                continue
        raise first_exc


def analyze_contract(
    text: str,
    provider: Optional[BaseProvider] = None,
    provider_name: str = "auto",
    perspective: str = "neutral",
    memory: Optional[MemoryStore] = None,
    use_memory: bool = True,
    save: bool = True,
    playbook: Optional[Playbook] = None,
    explain: bool = False,
    allow_fallback: bool = True,
    use_cache: bool = True,
    force: bool = False,
    client: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run a full analysis pipeline over contract text and return a dict with
    the AnalysisResult plus trend/memory metadata. This is the single
    function the CLI, the GitHub Action, the web dashboard, and any future
    integration all call.

    If use_cache is True and this exact contract text (by hash) was
    already analyzed before, the cached result is reused instead of
    calling the provider again - saving a paid or rate-limited API call
    on repeat runs. Pass force=True to bypass the cache.
    """
    playbook = playbook or Playbook()
    memory = memory or MemoryStore()
    h = file_hash(text)
    obligations = extract_obligations(text)

    cached = memory.find_by_hash(h) if (use_cache and not force) else None
    if cached:
        result = AnalysisResult(**cached["full_result"])
        if explain:
            result.clauses = attach_explanations(result.clauses)
        return {
            "result": result,
            "hash": h,
            "trend": None,
            "red_flags": [c for c in result.clauses if c.get("is_red_flag")],
            "obligations": obligations,
            "fallback_note": None,
            "from_cache": True,
        }

    provider = provider or get_provider(provider_name)
    if provider.name == "offline":
        provider.playbook = playbook
    context = _memory_context_for(memory, text) if use_memory else ""
    addendum = playbook.prompt_addendum()
    if addendum:
        context = f"{context}\n\nFirm playbook instructions:\n{addendum}" if context else addendum

    if allow_fallback:
        result, fallback_note = _analyze_with_fallback(provider, text, perspective, context)
    else:
        result, fallback_note = provider.analyze(text, perspective=perspective, memory_context=context), None

    if explain:
        result.clauses = attach_explanations(result.clauses)

    trend = None
    if use_memory:
        prior = memory.find_by_party(result.parties) if result.parties != "Unknown" else []
        if prior:
            prev = prior[-1]
            prev_rank = RISK_RANK.get(prev.get("risk_level", ""), 0)
            curr_rank = RISK_RANK.get(result.overall_risk, 0)
            if curr_rank > prev_rank:
                trend = "WORSE"
            elif curr_rank < prev_rank:
                trend = "IMPROVED"
            else:
                trend = "UNCHANGED"

    if save:
        memory.write(
            {
                "type": "contract_analyzed",
                "contract_type": result.contract_type,
                "parties": result.parties,
                "risk_level": result.overall_risk,
                "verdict": result.verdict,
                "contract_hash": h,
                "language": result.language,
                "findings_count": len(result.clauses),
                "provider": result.provider,
                "perspective": perspective,
                "obligations": obligations,
                "flagged_clauses": [c["name"] for c in result.clauses if c.get("is_red_flag")],
                "full_result": result.to_dict(),
                "client": client,
            }
        )

    return {
        "result": result,
        "hash": h,
        "trend": trend,
        "red_flags": [c for c in result.clauses if c.get("is_red_flag")],
        "obligations": obligations,
        "fallback_note": fallback_note,
        "from_cache": False,
    }


def compare_contracts(text_a: str, text_b: str, provider: Optional[BaseProvider] = None) -> Dict[str, Any]:
    """Analyze two versions of a contract independently and diff their clause scores."""
    provider = provider or get_provider("auto")
    result_a = provider.analyze(text_a)
    result_b = provider.analyze(text_b)

    by_name_a = {c["name"]: c for c in result_a.clauses}
    by_name_b = {c["name"]: c for c in result_b.clauses}
    all_names = sorted(set(by_name_a) | set(by_name_b))

    rows: List[Dict[str, Any]] = []
    for name in all_names:
        a = by_name_a.get(name)
        b = by_name_b.get(name)
        score_a = a["score"] if a else None
        score_b = b["score"] if b else None
        if score_a is None:
            status = "ADDED"
        elif score_b is None:
            status = "REMOVED"
        elif score_b < score_a:
            status = "IMPROVED"
        elif score_b > score_a:
            status = "WORSE"
        else:
            status = "UNCHANGED"
        rows.append({"clause": name, "score_v1": score_a, "score_v2": score_b, "status": status})

    return {
        "v1": result_a,
        "v2": result_b,
        "rows": rows,
        "risk_changed": result_a.overall_risk != result_b.overall_risk,
    }
