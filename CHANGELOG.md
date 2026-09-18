# Changelog

All notable changes to this project are documented in this file.

## [2.0.0] - Unreleased

Complete rebuild from a hackathon demo script into a standalone,
installable package.

### Added
- Installable `hermes-legal-advisor` package with a `hermes-legal` console
  command (`pip install hermes-legal-advisor`).
- Multi-provider architecture: Groq, Google Gemini, OpenRouter, and Ollama,
  plus a zero-dependency offline rule-based scanner that needs no API key.
- Automatic provider detection (`--provider auto`, the default) and a
  `hermes-legal providers` command to inspect what's configured.
- PDF and DOCX contract ingestion, in addition to plain text.
- Position-aware analysis via `--perspective` (client, vendor, contractor,
  employer, employee, tenant, landlord, or neutral).
- Redline export: a focused Markdown report (`--redline`) and an optional
  DOCX memo (`--redline-docx`) containing only the clauses that need
  renegotiation, with suggested replacement language.
- Batch mode (`hermes-legal batch <folder>`) with a CSV summary across an
  entire folder of contracts.
- `--fail-on-risk` flag for CI usage: exit non-zero when a contract crosses
  a chosen risk threshold.
- A reusable GitHub Action (`action.yml`) that scans contract files changed
  in a pull request and posts a summary to the job's step summary.
- Full test suite covering the offline provider, document ingestion, and
  the analysis engine.

### Changed
- README rewritten to lead with installation and free-tier usage rather
  than hackathon framing.
- The original Hermes-agent skill definition and Atropos RL training
  environment moved to `extras/` and documented in `docs/ADVANCED.md` -
  still included, no longer the headline.
- Memory store moved to `~/.hermes-legal/` (previously `~/.hermes/legal/`).

## [1.2.0] - Concurrent Execution (hackathon submission)
- Concurrent clause scoring via `ThreadPoolExecutor`.

## [1.1.0] - Compare & Watch (hackathon submission)
- Version comparison mode.
- Watch mode.
- Chat mode.

## [1.0.0] - Initial Release (hackathon submission)
- 9-clause risk scoring with SIGN/NEGOTIATE/REJECT verdict.
- English and Turkish support with auto language detection.
- Negotiation text suggestions for critical clauses.
- Missing clause detection.
- Memory of every analyzed contract.
