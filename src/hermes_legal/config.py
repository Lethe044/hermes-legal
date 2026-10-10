"""
Default options from a config file.

Instead of repeating `--provider groq --redact --perspective client` on
every command, put them once in ~/.hermes-legal/config.yaml (or the folder
named by HERMES_LEGAL_HOME, or the file named by HERMES_LEGAL_CONFIG).

Anything given on the command line always wins over the config file. A
bad value never crashes the tool: it is ignored with a warning, and the
built-in default is used instead.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# config key -> (argparse dest, validator description)
KEY_TO_DEST = {
    "provider": "provider",
    "perspective": "perspective",
    "client": "client",
    "parallel": "parallel",
    "redact": "redact",
    "redact_names": "redact_name",
    "explain": "explain",
    "fail_on_risk": "fail_on_risk",
}

EXAMPLE_CONFIG = """\
# Hermes Legal Advisor - default options
#
# Anything set here is used when you do not pass the matching flag on the
# command line. Flags always win. Delete or comment out any line you do not need.

# Which backend to use: auto, groq, gemini, openrouter, ollama, offline
# provider: auto

# Whose side you usually review for: neutral, client, vendor, contractor,
# employer, employee, tenant, landlord
# perspective: neutral

# Tag every analysis with this client or matter name
# client: "Acme Corp"

# Privacy mode: mask emails, phones, IBANs, ID numbers and the names below
# before any text goes to a hosted provider (Groq, Gemini, OpenRouter).
# Use --no-redact on the command line to switch it off for one run.
# redact: true
# redact_names:
#   - "Acme Corp"
#   - "Jane Doe"

# Always add plain-English explanations (--no-explain turns it off for one run)
# explain: false

# Number of contracts analyzed at the same time in batch mode
# parallel: 1

# Exit with an error when a contract reaches one of these levels (for CI)
# fail_on_risk: "CRITICAL,HIGH"
"""


def config_path() -> Path:
    explicit = os.environ.get("HERMES_LEGAL_CONFIG")
    if explicit:
        return Path(explicit)
    home = os.environ.get("HERMES_LEGAL_HOME")
    base = Path(home) if home else Path.home() / ".hermes-legal"
    return base / "config.yaml"


def _validate(key: str, value: Any) -> Tuple[bool, Optional[str]]:
    from .providers import PROVIDER_REGISTRY

    if key == "provider":
        ok = isinstance(value, str) and (value == "auto" or value in PROVIDER_REGISTRY)
        return ok, "must be auto or one of: " + ", ".join(PROVIDER_REGISTRY)
    if key in ("perspective", "client", "fail_on_risk"):
        return isinstance(value, str) and bool(value.strip()), "must be a non-empty text value"
    if key == "parallel":
        return isinstance(value, int) and not isinstance(value, bool) and value >= 1, "must be a whole number, 1 or more"
    if key in ("redact", "explain"):
        return isinstance(value, bool), "must be true or false"
    if key == "redact_names":
        return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value), "must be a list of names"
    return False, "unknown option"


def load_config(path: Optional[Path] = None) -> Tuple[Dict[str, Any], List[str]]:
    """Return (valid_options, warnings). Never raises for a missing or broken file."""
    p = Path(path) if path else config_path()
    if not p.exists():
        return {}, []
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as exc:
        return {}, [f"{p} could not be read and was ignored ({exc.__class__.__name__})"]
    if not isinstance(data, dict):
        return {}, [f"{p} must contain 'key: value' lines; ignored"]

    valid: Dict[str, Any] = {}
    warnings: List[str] = []
    for key, value in data.items():
        if key not in KEY_TO_DEST:
            warnings.append(f"unknown option '{key}' ignored (known: {', '.join(KEY_TO_DEST)})")
            continue
        ok, why = _validate(key, value)
        if not ok:
            warnings.append(f"option '{key}' ignored: {why}")
            continue
        valid[key] = value
    return valid, warnings


def apply_config_defaults(parser: argparse.ArgumentParser, config: Dict[str, Any]) -> None:
    """Use config values as the defaults of every sub-command that has a matching option."""
    if not config:
        return
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for sub in action.choices.values():
            dests = {a.dest for a in sub._actions}
            defaults = {
                KEY_TO_DEST[k]: (list(v) if isinstance(v, list) else v)
                for k, v in config.items()
                if KEY_TO_DEST[k] in dests
            }
            if defaults:
                sub.set_defaults(**defaults)


def write_example_config(path: Optional[Path] = None, overwrite: bool = False) -> Tuple[Path, bool]:
    """Write the example config. Returns (path, written). Never overwrites unless asked."""
    p = Path(path) if path else config_path()
    if p.exists() and not overwrite:
        return p, False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    return p, True
