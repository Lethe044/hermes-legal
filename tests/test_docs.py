from pathlib import Path

from hermes_legal.cli import build_parser
from hermes_legal.docgen import generate

ROOT = Path(__file__).parent.parent


def _command_names():
    import argparse

    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices)
    return []


def test_command_reference_is_up_to_date():
    committed = (ROOT / "docs" / "COMMANDS.md").read_text(encoding="utf-8")
    assert committed == generate(), (
        "docs/COMMANDS.md is out of date. Run: python -m hermes_legal.docgen > docs/COMMANDS.md"
    )


def test_every_command_is_documented_in_the_command_reference():
    reference = (ROOT / "docs" / "COMMANDS.md").read_text(encoding="utf-8")
    for name in _command_names():
        assert f"`hermes-legal {name}`" in reference, f"{name} missing from docs/COMMANDS.md"


def test_every_command_is_mentioned_in_the_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in _command_names():
        assert f"hermes-legal {name}" in readme, f"README never shows 'hermes-legal {name}'"
