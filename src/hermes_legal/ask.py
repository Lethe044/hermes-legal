"""
Ask a specific contract a direct question - "what's the termination notice
period", "who owns the IP", "can I be sued personally". This is different
from chat mode, which talks about analysis history; `ask` is grounded in
one document's actual text.

With an LLM provider configured, the question and contract text go
straight to the model. With the offline provider (or no provider
available), a simple keyword-overlap search finds the most relevant
paragraph(s) and returns those verbatim - not as smart, but still useful
and still completely free.
"""

from __future__ import annotations

import re
from typing import List

from .providers import BaseProvider


def _split_paragraphs(text: str) -> List[str]:
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def _keyword_search_answer(text: str, question: str, top_n: int = 2) -> str:
    stopwords = {
        "the", "is", "a", "an", "of", "to", "in", "for", "and", "or", "what",
        "who", "how", "does", "do", "can", "i", "my", "this", "that", "be",
        "are", "on", "if", "will", "shall",
    }
    q_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", question) if w.lower() not in stopwords}
    if not q_words:
        return "I couldn't identify any keywords in that question to search for."

    paragraphs = _split_paragraphs(text)
    scored = []
    for p in paragraphs:
        p_words = {w.lower() for w in re.findall(r"[a-zA-Z]+", p)}
        overlap = len(q_words & p_words)
        if overlap:
            scored.append((overlap, p))

    if not scored:
        return (
            "No offline provider match found for that question. Try rephrasing with "
            "words that appear in the contract, or configure an LLM provider "
            "(Groq/Gemini/OpenRouter/Ollama) for a real answer."
        )

    scored.sort(key=lambda x: -x[0])
    top = [p for _, p in scored[:top_n]]
    return (
        "Offline keyword search found this likely relevant text (not an AI-generated "
        "answer - configure an LLM provider for a direct answer):\n\n"
        + "\n\n---\n\n".join(top)
    )


def ask_contract(text: str, question: str, provider: BaseProvider) -> str:
    if provider.name == "offline":
        return _keyword_search_answer(text, question)

    prompt = (
        "You are Hermes Legal Advisor. Answer the following question using ONLY the "
        "contract text provided below. If the answer isn't in the contract, say so "
        "clearly rather than guessing. Keep the answer concise (a few sentences). "
        "Always note that this is not legal advice.\n\n"
        f"Contract text:\n\"\"\"\n{text[:12000]}\n\"\"\"\n\nQuestion: {question}"
    )

    name = provider.name
    if name == "groq":
        from groq import Groq

        client = Groq(api_key=provider.api_key)
        resp = client.chat.completions.create(
            model=provider.model, messages=[{"role": "user", "content": prompt}], max_tokens=600,
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
            model=provider.model, messages=[{"role": "user", "content": prompt}], max_tokens=600,
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
            return json.loads(resp.read().decode("utf-8")).get("response", "")
    return _keyword_search_answer(text, question)
