# Command reference

This file is generated from the command line parser by
`python -m hermes_legal.docgen`. Do not edit it by hand: change the
option in `src/hermes_legal/cli.py` and regenerate.

Run `hermes-legal <command> --help` for the same information in your terminal.

## `hermes-legal analyze`

Analyze a single contract file.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `contract`: Path to a .txt, .md, .pdf, or .docx contract file.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--perspective`: Whose side you're reviewing for: client, vendor, contractor, employer, employee, tenant, landlord, neutral. (default: `neutral`)
- `--output`: Save the full Markdown report to this path.
- `--output-pdf`: Save a professional PDF report to this path (requires reportlab).
- `--redline`: Save a Markdown redline (only flagged clauses) to this path.
- `--redline-docx`: Save a DOCX redline memo to this path (requires python-docx).
- `--redline-inline`: Save an edited copy of the original .docx with suggestions inserted inline (requires .docx input and python-docx).
- `--playbook`: Path to a firm playbook YAML file (default: ~/.hermes-legal/playbook.yaml if present).
- `--format`: Output format for stdout (default: text). (choices: text, json)
- `--explain`: Add plain-English explanations of each clause category.
- `--no-explain`: Turn plain-English explanations off for this run (overrides a config file default).
- `--no-fallback`: Do not automatically fall back to another provider if the chosen one fails.
- `--no-cache`: Do not reuse a cached result for identical contract text.
- `--force`: Re-analyze even if this exact contract was analyzed before (bypasses cache).
- `--include`: Additional file(s) (exhibits/addenda) to append and analyze as one contract package. Repeatable.
- `--client`: Tag this analysis with a client/matter name for portfolio and history filtering.
- `--no-ocr`: Do not fall back to OCR for scanned PDFs with no extractable text.
- `--no-save`: Do not write this analysis to memory.
- `--fail-on-risk`: Comma-separated risk levels that should cause a non-zero exit code (useful in CI), e.g. CRITICAL,HIGH

## `hermes-legal batch`

Analyze every contract in a folder.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `folder`: Folder containing contract files.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--perspective`:  (default: `neutral`)
- `--reports-dir`: Where to write per-file reports and the CSV summary.
- `--client`: Tag every analysis in this batch with a client/matter name.
- `--output-xlsx`: Also save a formatted Excel (.xlsx) summary (requires openpyxl).
- `--recursive`: Also analyze contracts in sub-folders.
- `--parallel`: Number of contracts to analyze concurrently (useful with hosted LLM providers). Default: 1 (sequential).
- `--no-browser`: Do not auto-open the generated HTML dashboard.

## `hermes-legal compare`

Compare two versions of a contract.

- `v1`: Path to the first (older) version.
- `v2`: Path to the second (newer) version.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--text`: Also show a line-by-line diff of the actual contract text.

## `hermes-legal watch`

Watch a folder and auto-analyze new contracts dropped into it.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `folder`: Folder to watch.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--perspective`:  (default: `neutral`)
- `--webhook`: Slack or Discord incoming webhook URL for risk alerts.
- `--alert-on`: Comma-separated risk levels that trigger a webhook alert. (default: `CRITICAL,HIGH`)

## `hermes-legal chat`

Interactive chat about your analyzed contracts.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).

## `hermes-legal providers`

List available providers and their configuration status.

## `hermes-legal playbook`

Manage firm/personal playbook customization.

### `hermes-legal playbook init`

Write an example playbook.yaml to customize.

- `--path`: Where to write it (default: ~/.hermes-legal/playbook.yaml)

## `hermes-legal clients`

List client/matter tags and how many contracts each has.

## `hermes-legal mcp`

Run an MCP server so AI assistants (Claude Desktop and others) can analyze contracts as a tool.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--allow-dir`: Folder the assistant may read contracts from. Repeatable. Default: the current folder only.

## `hermes-legal config`

Create or inspect the config file with your default options.

### `hermes-legal config init`

Write an example config file (all options commented out).

- `--force`: Overwrite an existing config file.

### `hermes-legal config show`

Show the options currently set and any problems.

### `hermes-legal config path`

Print where the config file lives.

## `hermes-legal clause`

Browse the model replacement clause library.

- `name`: Clause name, e.g. Termination, Liability, Non-Compete.

## `hermes-legal doctor`

Check your environment: dependencies, keys, OCR, local models.

## `hermes-legal export`

Bundle every report for a client (or everyone) into one ZIP.

- `--client`: Only export contracts tagged with this client. Omit to export everything.
- `--output`: Output ZIP path (default: <client>_bundle.zip).

## `hermes-legal history`

Show previously analyzed contracts.

- `--query`: Filter by any text (party name, contract type, etc).
- `--client`: Filter to only this client/matter tag.
- `--limit`: Max rows to show (default 20).

## `hermes-legal generate`

Generate a new contract from a template, for free, offline.

- `template`: Template key, e.g. nda, freelance, employment, service.
- `--list`: List available templates and their fields.
- `--field`: Set a field value as key=value. Repeatable.
- `--interactive`: Prompt for any missing fields.
- `--output`: Output file path.

## `hermes-legal serve`

Launch a local web dashboard for drag-and-drop contract analysis.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `--host`:  (default: `127.0.0.1`)
- `--port`:  (default: `8765`)
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).
- `--no-browser`: Do not auto-open a browser tab.
- `--api-key`: Require this key (header X-API-Key or ?key= in the URL) to use the dashboard. Also read from HERMES_LEGAL_API_KEY. Strongly recommended if binding to a non-localhost host.

## `hermes-legal ask`

Ask a specific contract a direct question.

- `--redact`: Privacy mode: mask emails, phones, IBANs, ID numbers and named parties before text goes to a hosted provider (Groq, Gemini, OpenRouter).
- `--no-redact`: Turn privacy mode off for this run (overrides a config file default).
- `--redact-name`: A name (person or company) to mask in privacy mode. Repeatable.
- `contract`: Path to a .txt, .md, .pdf, or .docx contract file.
- `question`: Your question, e.g. 'what is the termination notice period?'
- `--provider`: LLM backend to use: groq, gemini, openrouter, ollama, offline, or auto (default: auto-detect).

## `hermes-legal deadlines`

List time-bound obligations extracted from analyzed contracts.

- `--limit`:  (default: `20`)

## `hermes-legal portfolio`

Generate an aggregate HTML dashboard across every contract ever analyzed.

- `--output`: Output HTML path (default: portfolio_dashboard.html).
- `--client`: Restrict the dashboard to only this client/matter tag.
- `--no-browser`:
