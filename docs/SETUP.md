# Setup

## Requirements

- Python 3.9 or newer

## Install

```bash
pip install hermes-legal-advisor[all]
```

Extras, if you want a smaller install:

| Extra | Adds |
|---|---|
| `groq` | Groq client (free-tier LLM analysis) |
| `gemini` | Google Generative AI client (free-tier LLM analysis) |
| `openrouter` | OpenAI-compatible client for OpenRouter |
| `pdf` | PDF reading via `pypdf` |
| `docx` | Word document reading/writing via `python-docx` |
| `all` | everything above |
| `dev` | `pytest`, `pytest-cov` for running the test suite |

You can also run entirely without any extra: the offline rule-based provider
and `.txt`/`.md` file support work with just the base install.

## From source

```bash
git clone https://github.com/Lethe044/hermes-legal.git
cd hermes-legal
pip install -e ".[all,dev]"
pytest
```

## Configuration

All configuration is done via environment variables - there is no config
file to manage.

| Variable | Used by |
|---|---|
| `GROQ_API_KEY` | Groq provider |
| `GEMINI_API_KEY` | Gemini provider |
| `OPENROUTER_API_KEY` | OpenRouter provider |
| `OLLAMA_HOST` | Ollama provider (default `http://localhost:11434`) |

Run `hermes-legal providers` at any time to see which of these are detected
and which provider will be used automatically.

## Where data is stored

Every analyzed contract's metadata (type, parties, risk level, verdict -
never the raw contract text) is appended to
`~/.hermes-legal/contracts_memory.jsonl`. Full Markdown reports are written
to `~/.hermes-legal/reports/` by default, or to a directory you specify with
`--output`, `--redline`, or `--reports-dir`.

To reset all history, simply delete `~/.hermes-legal/`.

## Uninstall

```bash
pip uninstall hermes-legal-advisor
rm -rf ~/.hermes-legal
```
