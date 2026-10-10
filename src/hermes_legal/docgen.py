"""
Generates docs/COMMANDS.md from the real command line parser, so the
reference can never drift from what the tool actually accepts.

Regenerate after changing any command or option:

    python -m hermes_legal.docgen > docs/COMMANDS.md
"""

from __future__ import annotations

import argparse
import sys
from typing import List

HEADER = """# Command reference

This file is generated from the command line parser by
`python -m hermes_legal.docgen`. Do not edit it by hand: change the
option in `src/hermes_legal/cli.py` and regenerate.

Run `hermes-legal <command> --help` for the same information in your terminal.
"""


def _option_line(action: argparse.Action) -> str:
    if action.option_strings:
        name = ", ".join(f"`{o}`" for o in action.option_strings)
    else:
        name = f"`{action.dest}`"
    help_text = (action.help or "").replace("%(default)s", str(action.default))
    extras = []
    if action.choices and not isinstance(action.choices, dict):
        extras.append("choices: " + ", ".join(str(c) for c in action.choices))
    default = action.default
    shows_default = (
        action.option_strings
        and not isinstance(action, argparse._StoreFalseAction)  # "--no-x" flags: the stored value is not a default
        and default not in (None, False, argparse.SUPPRESS, [], "")
        and "default" not in help_text.lower()  # the help text already says it
    )
    if shows_default:
        extras.append(f"default: `{default}`")
    suffix = f" ({'; '.join(extras)})" if extras else ""
    return f"- {name}: {help_text}{suffix}".rstrip()


def _describe(parser: argparse.ArgumentParser, name: str, help_text: str, level: int) -> List[str]:
    lines = [f"{'#' * level} `{name}`", ""]
    if help_text:
        lines += [help_text, ""]
    options = [a for a in parser._actions if not isinstance(a, (argparse._HelpAction, argparse._SubParsersAction))]
    if options:
        lines += [_option_line(a) for a in options] + [""]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {a.dest: a.help for a in action._choices_actions}
            for sub_name, sub_parser in action.choices.items():
                lines += _describe(sub_parser, f"{name} {sub_name}", helps.get(sub_name, ""), level + 1)
    return lines


def generate() -> str:
    from .cli import build_parser

    parser = build_parser()
    lines: List[str] = [HEADER]
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            helps = {a.dest: a.help for a in action._choices_actions}
            for name, sub_parser in action.choices.items():
                lines += _describe(sub_parser, f"hermes-legal {name}", helps.get(name, ""), 2)
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    sys.stdout.write(generate())
