# Hermes Legal Advisor

[![PyPI version](https://img.shields.io/pypi/v/hermes-legal-advisor.svg)](https://pypi.org/project/hermes-legal-advisor/)
[![PyPI downloads](https://img.shields.io/pypi/dm/hermes-legal-advisor.svg)](https://pypi.org/project/hermes-legal-advisor/)
[![Python versions](https://img.shields.io/pypi/pyversions/hermes-legal-advisor.svg)](https://pypi.org/project/hermes-legal-advisor/)
[![CI](https://github.com/Lethe044/hermes-legal/actions/workflows/ci.yml/badge.svg)](https://github.com/Lethe044/hermes-legal/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

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
| **Ask mode** | Ask a specific contract a direct question, grounded in that document's own text |
| **Plain-English mode** | `--explain` translates legal jargon into everyday language for each flagged clause |
| **Provider fallback** | If your chosen provider fails (rate limit, outage), it automatically retries with the next available one |
| **Deadline tracking** | Extracts term lengths, renewal windows, and notice periods across every contract you've analyzed |
| **Portfolio dashboard** | `hermes-legal portfolio` aggregates risk trends and top red flags across your entire contract history |
| **Result caching** | Re-analyzing the exact same contract reuses the cached result instead of spending another API call |
| **Contract packages** | `--include` merges exhibits and addenda into one analysis alongside the main agreement |
| **True inline redlines** | `--redline-inline` inserts suggestions directly into a copy of your original .docx, not just a separate memo |
| **Real Word Track Changes** | Inline redlines use actual OOXML tracked-change markup, opening in Word's Review pane like a human edit |
| **Client/matter tagging** | `--client` organizes contracts by client so history, portfolio, and dashboards can be filtered per client |
| **Excel batch reports** | `--output-xlsx` produces a color-coded Excel summary, the format most firms actually work in |
| **Docker support** | Run the web dashboard anywhere with one `docker run`, no Python install needed |
| **API key protection** | Optional `--api-key` on `serve` for safely exposing the dashboard beyond localhost |
| **Parallel batch mode** | `--parallel N` analyzes multiple contracts concurrently, much faster with hosted providers |
| **Client bundles** | `hermes-legal export` zips every report for a client into one file to send |

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

### Ask a contract a direct question

```bash
hermes-legal ask contract.pdf "what is the termination notice period?"
```

With an LLM provider configured, this grounds the answer in the actual
contract text. With the offline provider, it falls back to a free
keyword search over the document instead of guessing.

### Plain-English explanations

```bash
hermes-legal analyze contract.txt --explain
```

Adds an "In Plain English" section translating each flagged clause's
legal language into everyday terms - useful for anyone who isn't a lawyer.

### Track deadlines across every contract

```bash
hermes-legal deadlines
```

Lists term lengths, auto-renewal cancellation windows, and termination
notice periods extracted from every contract you've analyzed, soonest
first - so you don't have to reread old contracts to remember what's
coming up.

### Portfolio dashboard

```bash
hermes-legal portfolio
```

Generates an HTML dashboard aggregating every contract you've ever
analyzed: risk distribution, your most common red flags, and a
per-counter-party breakdown with their highest risk seen and latest
verdict. Useful for anyone tracking more than a handful of contracts.

### Contract packages (main agreement + exhibits)

```bash
hermes-legal analyze main_agreement.pdf --include exhibit_a.pdf --include exhibit_b.docx
```

Merges the main file with any number of `--include` attachments and
analyzes them as a single contract package.

### Skip redundant API calls

```bash
hermes-legal analyze contract.txt --force
```

By default, re-analyzing the exact same contract text reuses the cached
result instead of calling a paid or rate-limited API again. Pass
`--force` to bypass the cache, or `--no-cache` to disable caching for
one run without affecting future runs.

### True inline redlines (edits your actual .docx)

```bash
hermes-legal analyze contract.docx --redline-inline redlined_contract.docx
```

Unlike `--redline-docx` (a separate memo), this inserts each suggestion
directly into a copy of your original document, right after the clause
it concerns - closer to what a human reviewer would hand back.

### True inline redlines (edits your actual .docx)

```bash
hermes-legal analyze contract.docx --redline-inline redlined_contract.docx
```

This inserts each suggestion as a real Word **Tracked Change** directly
into a copy of your original document, right after the clause it
concerns. Open the result in Word and it shows up in the Review pane
exactly like a human editor's tracked edit - accept, reject, or comment
on each one individually.

### Organize by client or matter

```bash
hermes-legal analyze contract.txt --client "Acme Corp"
hermes-legal clients
hermes-legal history --client "Acme Corp"
hermes-legal portfolio --client "Acme Corp"
```

Tag any analysis with `--client`, then filter history, the portfolio
dashboard, or a batch run to just that client - useful the moment you're
handling more than one.

### Excel batch reports

```bash
hermes-legal batch ./contracts_folder --output-xlsx summary.xlsx
```

Produces a color-coded Excel workbook (risk and verdict cells shaded)
alongside the usual CSV and HTML dashboard. Requires
`pip install hermes-legal-advisor[xlsxreport]` (included in `[all]`).

### Run it with Docker

```bash
docker build -t hermes-legal .
docker run -p 8765:8765 -v hermes_data:/data hermes-legal
```

Starts the web dashboard at `http://localhost:8765` with zero local
Python setup. Add `-e GROQ_API_KEY=...` (or Gemini/OpenRouter) for
LLM-backed analysis, or leave it out to use the free offline scanner. The
mounted volume persists analysis history across container restarts.

### Protect the dashboard with an API key

```bash
hermes-legal serve --host 0.0.0.0 --api-key mysecret
```

Required if you expose `serve` beyond `127.0.0.1` (a shared server, a
Docker container on a network others can reach). Every API call needs
`X-API-Key: mysecret`, or you can open
`http://host:8765/?key=mysecret` and the page fills it in automatically.
Can also be set via `HERMES_LEGAL_API_KEY`.

### Speed up large batches

```bash
hermes-legal batch ./contracts_folder --parallel 5
```

Analyzes multiple contracts concurrently instead of one at a time -
mainly useful with a hosted provider (Groq, Gemini, OpenRouter) where
each analysis is a network call. Defaults to sequential (`--parallel 1`).

### Bundle everything for a client

```bash
hermes-legal export --client "Acme Corp" --output acme_bundle.zip
```

Zips every stored report, a CSV summary, and an HTML dashboard for one
client (or everyone, if `--client` is omitted) into a single file ready
to email or archive.

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
- [`SECURITY.md`](SECURITY.md) - supported versions and how to report a vulnerability
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) - community standards

## Contributing

Issues and pull requests are welcome - see `CONTRIBUTING.md` for the shape of
a good contribution (a new red-flag pattern, a new provider, a new report
format are all good first PRs).

## Disclaimer

Hermes Legal Advisor provides contract analysis, not legal advice. Always
consult a qualified attorney before signing any contract.
