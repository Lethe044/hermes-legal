from __future__ import annotations

from typing import Dict, Optional, Type

from .base import AnalysisResult, BaseProvider, ProviderError
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .offline_provider import OfflineProvider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider

PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
    "ollama": OllamaProvider,
    "offline": OfflineProvider,
}

# Order matters: prefer the fastest genuinely-free hosted options first,
# fall back to local, and finally the zero-dependency offline scanner.
AUTO_DETECT_ORDER = ["groq", "gemini", "openrouter", "ollama", "offline"]


def get_provider(name: Optional[str] = None) -> BaseProvider:
    """
    Resolve a provider by name, or auto-detect the best available one.

    Auto-detection walks AUTO_DETECT_ORDER and returns the first provider
    that reports itself as available (has an API key / reachable local
    server). The offline provider is always available, so this function
    never raises for lack of configuration - at worst you get the
    rule-based scanner.
    """
    if name and name != "auto":
        cls = PROVIDER_REGISTRY.get(name)
        if cls is None:
            raise ProviderError(
                f"Unknown provider '{name}'. Choices: {', '.join(PROVIDER_REGISTRY)}, or 'auto'."
            )
        return cls()

    for candidate in AUTO_DETECT_ORDER:
        instance = PROVIDER_REGISTRY[candidate]()
        if instance.is_available():
            return instance
    return OfflineProvider()  # unreachable in practice, but keeps type-checkers happy


__all__ = [
    "AnalysisResult",
    "BaseProvider",
    "ProviderError",
    "PROVIDER_REGISTRY",
    "AUTO_DETECT_ORDER",
    "get_provider",
]
