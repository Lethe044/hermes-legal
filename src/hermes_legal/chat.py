from __future__ import annotations

from typing import Optional

from .memory.store import MemoryStore
from .providers import get_provider, ProviderError


def _build_context(memory: MemoryStore, limit: int = 10) -> str:
    contracts = memory.contracts()
    if not contracts:
        return "No contracts have been analyzed yet."
    lines = ["Contracts analyzed so far:"]
    for c in contracts[-limit:]:
        lines.append(
            f"- [{c.get('timestamp', '?')[:10]}] {c.get('contract_type', '?')} | "
            f"Parties: {c.get('parties', '?')} | Risk: {c.get('risk_level', '?')} | "
            f"Verdict: {c.get('verdict', '?')}"
        )
    return "\n".join(lines)


def run_chat_mode(provider_name: str = "auto", console=None):
    """
    A minimal chat loop over the analyzed-contract memory. Because
    providers are structured-JSON-only for the main analysis pipeline,
    chat mode uses the provider's raw text completion where available and
    otherwise falls back to a simple memory search/summary - it never
    hard-depends on any single vendor's SDK.
    """
    if console is None:
        from rich.console import Console
        console = Console()

    memory = MemoryStore()
    context = _build_context(memory)

    try:
        provider = get_provider(provider_name)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        return

    console.print(f"[cyan]Hermes Legal Advisor - chat mode (provider: {provider.name}).[/]")
    console.print("[dim]Ask about your analyzed contracts. Type 'exit' to leave.[/]\n")
    console.print(f"[dim]{context}[/]\n")

    if provider.name == "offline":
        console.print(
            "[yellow]The offline provider cannot hold a free-form conversation - "
            "it can only run pattern-based analysis. Configure Groq, Gemini, "
            "OpenRouter, or Ollama for chat mode.[/]"
        )
        return

    while True:
        try:
            user_input = console.input("[bold]You:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            return
        if user_input.lower() in ("exit", "quit", "q", "çıkış", "görüşürüz"):
            console.print("[dim]Goodbye![/]")
            return
        if not user_input:
            continue

        prompt = (
            "You are Hermes Legal Advisor in conversational mode. Answer questions "
            "about the user's previously analyzed contracts using the context below. "
            "Respond in the same language the user writes in. Always recommend "
            "consulting an attorney for anything binding.\n\n"
            f"{context}\n\nQuestion: {user_input}"
        )
        try:
            reply = provider.chat(prompt) if hasattr(provider, "chat") else _fallback_reply(provider, prompt)
        except Exception as exc:
            reply = f"(error talking to {provider.name}: {exc})"
        console.print(f"[green]Hermes:[/] {reply}\n")


def _fallback_reply(provider, prompt: str) -> str:
    """
    Providers in this project are built around one-shot structured
    analysis rather than open chat. For chat mode we ask for a plain-text
    answer by reusing the same underlying client where possible.
    """
    name = provider.name
    if name == "groq":
        from groq import Groq

        client = Groq(api_key=provider.api_key)
        resp = client.chat.completions.create(
            model=provider.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        return resp.choices[0].message.content or ""
    if name == "gemini":
        import google.generativeai as genai

        genai.configure(api_key=provider.api_key)
        model = genai.GenerativeModel(provider.model)
        return model.generate_content(prompt).text or ""
    if name == "openrouter":
        from openai import OpenAI

        client = OpenAI(api_key=provider.api_key, base_url="https://openrouter.ai/api/v1")
        resp = client.chat.completions.create(
            model=provider.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        return resp.choices[0].message.content or ""
    if name == "ollama":
        import json
        import urllib.request

        payload = json.dumps({"model": provider.model, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(
            f"{provider.host}/api/generate", data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            import json as _json
            return _json.loads(resp.read().decode("utf-8")).get("response", "")
    return "Chat is not supported for this provider."
