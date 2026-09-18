# Providers

Hermes Legal Advisor separates "how the analysis is written up" from "which
model does the thinking." You can swap providers with a single flag
(`--provider`) or let it auto-detect the best one you have configured.

## Comparison

| Provider | Cost | Setup effort | Best for |
|---|---|---|---|
| `offline` | Free forever, no signup | None | Instant first pass, CI without secrets, fully private/air-gapped use |
| `groq` | Free tier (generous rate limits) | 1 minute | Fast, high-quality analysis with zero cost |
| `gemini` | Free tier (generous rate limits) | 1 minute | Alternative free option, good for longer contracts |
| `ollama` | Free, fully local | 5-10 minutes (model download) | Confidential contracts that must never leave your machine |
| `openrouter` | Free `:free` models available, or bring your own paid model | 1 minute | Flexibility - swap in GPT, Claude, or any model OpenRouter hosts |

## Groq (recommended free option)

1. Create a free account at <https://console.groq.com>
2. Generate a key at <https://console.groq.com/keys>
3. `export GROQ_API_KEY=gsk_...`

## Gemini

1. Create a free API key at <https://aistudio.google.com/apikey>
2. `export GEMINI_API_KEY=...`

## OpenRouter

1. Create a key at <https://openrouter.ai/keys>
2. `export OPENROUTER_API_KEY=sk-or-...`
3. By default, Hermes Legal Advisor uses a `:free`-suffixed model on
   OpenRouter. To use a paid model instead, pass `--provider openrouter` and
   edit `DEFAULT_OPENROUTER_MODEL` in
   `src/hermes_legal/providers/openrouter_provider.py`, or open an issue if
   you'd like this exposed as a CLI flag.

## Ollama (fully local)

1. Install Ollama from <https://ollama.com>
2. `ollama pull llama3.1`
3. `ollama serve`
4. Hermes Legal Advisor will detect it automatically at
   `http://localhost:11434`, or set `OLLAMA_HOST` for a remote instance.

## Offline (zero-dependency rule engine)

No setup at all. Force it explicitly with `--provider offline`. It uses a
library of regex/keyword heuristics informed by publicly documented CUAD
(Contract Understanding Atticus Dataset) risk categories - fast and free,
but less nuanced than an LLM-backed pass. Good as an instant sanity check
before a deeper review, or in CI pipelines that shouldn't depend on secrets.

## Auto-detection order

`--provider auto` (the default) tries providers in this order and uses the
first one that is configured: `groq` -> `gemini` -> `openrouter` -> `ollama`
-> `offline`. The offline provider is always available, so a command never
fails purely for lack of an API key.
