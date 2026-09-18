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
| **Bilingual** | English and Turkish contract analysis, auto-detected |
| **GitHub Action** | Drop it into any repo's CI to auto-review contract files in pull requests |

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

Produces a `batch_summary.csv` plus one Markdown report per file.

### Version comparison

```bash
hermes-legal compare sample_contracts/freelance_contract.txt sample_contracts/freelance_contract_v2.txt
```

### Watch mode

```bash
hermes-legal watch ./contracts_inbox
```

### Chat mode

```bash
hermes-legal chat
```

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
│   ├── cli.py          # analyze / batch / compare / watch / chat / providers
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
