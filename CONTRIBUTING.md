# Contributing

Thanks for considering a contribution. This project is small enough that
most good first contributions fall into one of a few shapes:

## Add a red-flag pattern

The offline rule engine lives entirely in
`src/hermes_legal/providers/offline_provider.py`, in the `RULES` list. Each
rule is a dict with a clause name, one or more "presence" patterns, an
optional "red_flag" regex, scores, a finding message, and a suggested
replacement. Add a test case to `tests/test_offline_provider.py` alongside
any new rule - ideally one contract snippet that should trigger it and one
that shouldn't.

## Add a provider

Implement `BaseProvider` from `src/hermes_legal/providers/base.py` (just
`is_available()` and `analyze()`), register it in
`src/hermes_legal/providers/__init__.py`'s `PROVIDER_REGISTRY` and
`AUTO_DETECT_ORDER`, and document it in `docs/PROVIDERS.md`. Providers
should degrade gracefully - if the SDK isn't installed, raise a
`ProviderError` with a one-line fix, don't crash on import.

## Add a report format

Report generation lives in `src/hermes_legal/reports/`. Each format is a
pure function that takes an `AnalysisResult` and returns either a string
(Markdown/CSV) or writes a file (DOCX). Wire new formats into
`src/hermes_legal/cli.py`'s `cmd_analyze`/`cmd_batch` as a new flag.

## Development setup

```bash
git clone https://github.com/Lethe044/hermes-legal.git
cd hermes-legal
pip install -e ".[all,dev]"
pytest
```

## Pull requests

- Keep PRs focused on one change.
- Add or update tests for anything behavioral.
- Run `pytest` before opening the PR.
- Update `CHANGELOG.md` under an "Unreleased" heading.

## Reporting issues

Please include: the command you ran, the provider you were using
(`hermes-legal providers` output helps), and, if possible, a redacted
snippet of the contract text that triggered the problem.
