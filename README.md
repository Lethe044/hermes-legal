# Hermes Legal Advisor

**Free, multi-provider AI contract analysis for developers, freelancers, and small teams.**

Feed it a contract - a `.txt`, `.pdf`, or `.docx` file - and it reads every clause,
scores each one for risk, tells you which standard clauses are missing, suggests
concrete replacement language for the risky ones, and gives you a final
**SIGN / NEGOTIATE / REJECT** verdict. It remembers every contract it has ever
analyzed, so it can tell you when a recurring counter-party's terms are getting
worse over time.

It works with zero budget: a built-in offline rule engine needs no API key at
all, and free tiers on Groq and Google Gemini give you full LLM-grade analysis
at no cost. If you have a paid API key for a stronger model, you can plug that
in too - it is always optional, never required.

## Why this exists

Contract review tools either live inside a specific AI coding assistant, cost
money per review, or only handle plain text. Hermes Legal Advisor is a
standalone command-line tool and Python package: install it, point it at a
real contract file, and get a structured answer - no subscription, no vendor
lock-in, and it plugs straight into your GitHub workflow as a CI check.

## Key Features

| Feature | Description |
|---|---|
| **Free by default** | Offline rule-based scanner needs no signup at all; Groq and Gemini free tiers add full LLM analysis for $0 |
| **Real file support** | Reads `.txt`, `.md`, `.pdf`, and `.docx` contracts, not just plain text |
| **9+ clause risk scoring** | Termination, liability, IP, non-compete, confidentiality, payment, auto-renewal, dispute resolution, governing law |
| **Position-aware review** | Analyze as the client, vendor, contractor, employer, employee, tenant, or landlord - risk framing changes accordingly |
| **Redline suggestions** | Concrete replacement language for every flagged clause, exportable to Markdown or a DOCX memo |
| **Missing clause detection** | Flags standard clauses that should be there but aren't |
| **Memory & trend detection** | Remembers every contract analyzed and flags when a counter-party's terms get worse over time |
| **Batch mode** | Scan an entire folder of contracts and get a CSV summary plus per-file reports |
| **Version comparison** | Diff two drafts of the same contract clause-by-clause |
| **Watch mode** | Monitor a folder and auto-analyze anything dropped into it |
| **Chat mode** | Ask follow-up questions about anything already analyzed |
| **GitHub Action** | Drop it into any repo's CI to auto-review contract files in pull requests |
| **Contract generator** | Draft a new NDA, freelance, employment, or service agreement from scratch, for free, offline |
| **Web dashboard** | Drag-and-drop browser UI for non-technical users - no CLI required |
| **Firm playbook** | Customize risk thresholds and negotiation language to match your own house style, via one YAML file |
| **PDF reports** | Professional, brandable PDF output alongside Markdown and DOCX |
| **Multilingual** | Analyzes contracts in English, Turkish, Spanish, and German, auto-detected |
| **JSON output** | `--format json` for scripting and CI pipelines |
| **Batch dashboard** | Visual HTML risk summary generated automatically for every batch run |
| **Webhook alerts** | Watch mode can post to Slack or Discord when a high-risk contract appears |

## Risk Scoring

| Score | Level | Meaning |
|---|---|---|
| 9-10 | CRITICAL | Red flag - potentially unacceptable |
| 7-8 | HIGH | Significantly unfavorable - negotiate |
| 5-6 | MEDIUM | Worth noting - review carefully |
| 1-4 | LOW | Standard and acceptable |

## Install

```bash
pip install hermes-legal-advisor[all]
```

`[all]` pulls in every optional dependency (PDF/DOCX support, Groq, Gemini,
OpenRouter clients). If you only need one provider, install a narrower extra
instead, e.g. `pip install hermes-legal-advisor[groq,pdf]`.

Or run from source:

```bash
git clone https://github.com/Lethe044/hermes-legal.git
cd hermes-legal
pip install -e ".[all]"
```

## Pick a free provider

You do not need to configure anything to get started - the offline scanner
always works. For deeper LLM-backed analysis, pick one:

```bash
# Groq - free tier, very fast
export GROQ_API_KEY=gsk_...          # https://console.groq.com/keys

# Gemini - generous free tier
export GEMINI_API_KEY=...            # https://aistudio.google.com/apikey

# OpenRouter - access to many :free models, plus paid ones if you want them
export OPENROUTER_API_KEY=sk-or-...  # https://openrouter.ai/keys

# Ollama - fully local, fully private, needs no internet after setup
ollama pull llama3.1 && ollama serve
```

Hermes Legal Advisor auto-detects whichever of these is configured, in that
order, and falls back to the offline scanner if none are. Check what it sees:

```bash
hermes-legal providers
```

See `docs/PROVIDERS.md` for a full comparison and setup walkthrough.

## Quick Start

```bash
hermes-legal analyze sample_contracts/freelance_contract.txt
hermes-legal analyze sample_contracts/nda_contract.txt --perspective vendor
hermes-legal analyze contract.pdf --output report.md --redline redline.md
hermes-legal analyze contract.docx --redline-docx redline.docx
```

### Batch mode

```bash
hermes-legal batch ./contracts_folder
```

Produces a `batch_summary.csv`, a visual `dashboard.html` (opened
automatically unless you pass `--no-browser`), and one Markdown report
per file.

### Scripting / CI integration

```bash
hermes-legal analyze contract.txt --format json
```

Prints the full structured result as JSON to stdout instead of a
formatted table - pipe it into `jq`, a script, or another tool.

### Version comparison

```bash
hermes-legal compare sample_contracts/freelance_contract.txt sample_contracts/freelance_contract_v2.txt
```

### Watch mode

```bash
hermes-legal watch ./contracts_inbox
hermes-legal watch ./contracts_inbox --webhook https://hooks.slack.com/services/... --alert-on CRITICAL,HIGH
```

The `--webhook` flag posts an alert to Slack or Discord whenever a newly
dropped contract scores one of the risk levels in `--alert-on` (default:
CRITICAL and HIGH).

### Chat mode

```bash
hermes-legal chat
```

### Web dashboard (no CLI needed)

```bash
hermes-legal serve
```

Opens a browser tab at `http://127.0.0.1:8765` where anyone can drag and
drop a contract file and get an instant analysis - built for colleagues
or clients who will never touch a terminal. Uses only Python's standard
library, so it needs no extra install.

### Generate a new contract

```bash
hermes-legal generate --list
hermes-legal generate nda --field party_a="Acme Inc." --field party_b="Beta LLC" --output nda.txt
hermes-legal generate freelance --interactive
```

Produces a ready-to-edit draft entirely offline, for free. Any field you
don't supply is left as a clearly marked placeholder.

### Customize for your firm

```bash
hermes-legal playbook init
```

Writes an example `~/.hermes-legal/playbook.yaml` you can edit to set your
firm name, override any clause's risk score or negotiation language, add
entirely custom red-flag rules, or adjust the CRITICAL/HIGH/MEDIUM
thresholds - all without touching a line of code. Every `analyze`,
`batch`, and `serve` command picks it up automatically if present, or
point at a specific file with `--playbook path/to/file.yaml`.

### Professional PDF reports

```bash
hermes-legal analyze contract.pdf --output-pdf report.pdf
```

Requires `pip install hermes-legal-advisor[pdfreport]` (included in `[all]`).

## Use it in CI

Drop this into any repository to get an automatic risk summary whenever a
contract file changes in a pull request:

```yaml
# .github/workflows/contract-review.yml
on:
  pull_request:
    paths: ["contracts/**"]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Lethe044/hermes-legal@main
        with:
          path: contracts/
          fail-on-risk: CRITICAL
          groq-api-key: ${{ secrets.GROQ_API_KEY }}
```

No API key configured? Leave the `groq-api-key` line out entirely - the
action still runs, using the offline scanner.

## Automatic Red Flags

- Termination notice under 7 days
- Uncapped liability on one party only
- IP assignment covering personal-time work
- Non-compete longer than 2 years or with worldwide scope
- Auto-renewal with under 30 days' cancellation window
- Arbitration/dispute costs borne entirely by one party
- Perpetual/indefinite confidentiality obligations

## Project Structure

```
hermes-legal/
├── src/hermes_legal/
│   ├── providers/     # Groq, Gemini, OpenRouter, Ollama, offline rule engine
│   ├── ingest/         # .txt / .pdf / .docx readers
│   ├── analysis/       # orchestration, risk scoring, version diff
│   ├── reports/        # Markdown, CSV, DOCX redline generation
│   ├── memory/         # JSONL-backed contract history
│   ├── cli.py          # analyze / batch / compare / watch / chat / providers / generate / serve / playbook / history
│   ├── generator.py    # offline contract templates (NDA, freelance, employment, service)
│   ├── playbook.py     # firm-specific YAML customization
│   ├── webapp.py        # zero-dependency local web dashboard
│   ├── watch.py
│   └── chat.py
├── tests/
├── sample_contracts/
├── action.yml           # GitHub Action definition
└── docs/
```

## Documentation

- [`docs/SETUP.md`](docs/SETUP.md) - installation and configuration in depth
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md) - free-tier provider comparison and setup
- [`docs/ADVANCED.md`](docs/ADVANCED.md) - the project's origin as a Hermes/Atropos
  hackathon entry, and the reinforcement-learning reward function used to train it
- [`CONTRIBUTING.md`](CONTRIBUTING.md) - how to add a provider, a rule, or a report format
- [`CHANGELOG.md`](CHANGELOG.md) - version history

## Contributing

Issues and pull requests are welcome - see `CONTRIBUTING.md` for the shape of
a good contribution (a new red-flag pattern, a new provider, a new report
format are all good first PRs).

## Disclaimer

Hermes Legal Advisor provides contract analysis, not legal advice. Always
consult a qualified attorney before signing any contract.
