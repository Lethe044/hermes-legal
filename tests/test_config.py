import contextlib
import io
import json
import os
from pathlib import Path

from hermes_legal.cli import build_parser, main
from hermes_legal.config import (
    EXAMPLE_CONFIG, apply_config_defaults, config_path, load_config, write_example_config,
)

SAMPLE = Path(__file__).parent.parent / "sample_contracts" / "nda_contract.txt"


def _write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_missing_file_is_not_an_error(tmp_path):
    assert load_config(tmp_path / "nope.yaml") == ({}, [])


def test_valid_options_are_loaded(tmp_path):
    p = _write(tmp_path, "provider: offline\nperspective: client\nparallel: 3\nredact: true\nredact_names: [Acme]\nexplain: true\n")
    config, warnings = load_config(p)
    assert warnings == []
    assert config["provider"] == "offline"
    assert config["parallel"] == 3
    assert config["redact"] is True
    assert config["redact_names"] == ["Acme"]


def test_invalid_and_unknown_options_are_ignored_with_a_warning(tmp_path):
    p = _write(tmp_path, "provider: skynet\nparallel: 0\nredact: maybe\nbogus: 1\nperspective: client\n")
    config, warnings = load_config(p)
    assert config == {"perspective": "client"}
    assert len(warnings) == 4


def test_broken_yaml_never_crashes(tmp_path):
    p = _write(tmp_path, "provider: [unclosed\n")
    config, warnings = load_config(p)
    assert config == {}
    assert warnings


def test_non_mapping_yaml_is_ignored(tmp_path):
    config, warnings = load_config(_write(tmp_path, "- just\n- a list\n"))
    assert config == {} and warnings


def test_example_config_is_fully_commented_out_and_valid(tmp_path):
    p = _write(tmp_path, EXAMPLE_CONFIG)
    assert load_config(p) == ({}, [])


def test_write_example_never_overwrites_unless_asked(tmp_path):
    path, written = write_example_config(tmp_path / "c.yaml")
    assert written
    path.write_text("provider: offline\n", encoding="utf-8")
    _, written_again = write_example_config(tmp_path / "c.yaml")
    assert not written_again
    assert path.read_text(encoding="utf-8") == "provider: offline\n"
    _, forced = write_example_config(tmp_path / "c.yaml", overwrite=True)
    assert forced


def test_config_path_respects_environment(tmp_path, monkeypatch=None):
    old = {k: os.environ.get(k) for k in ("HERMES_LEGAL_CONFIG", "HERMES_LEGAL_HOME")}
    try:
        os.environ.pop("HERMES_LEGAL_CONFIG", None)
        os.environ["HERMES_LEGAL_HOME"] = str(tmp_path)
        assert config_path() == tmp_path / "config.yaml"
        os.environ["HERMES_LEGAL_CONFIG"] = str(tmp_path / "custom.yaml")
        assert config_path() == tmp_path / "custom.yaml"
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_config_becomes_defaults_but_flags_win():
    parser = build_parser()
    apply_config_defaults(parser, {"provider": "offline", "perspective": "client", "parallel": 4,
                                   "redact": True, "redact_names": ["Acme"], "explain": True})
    analyze = parser.parse_args(["analyze", "x.txt"])
    assert analyze.provider == "offline" and analyze.perspective == "client"
    assert analyze.redact is True and analyze.explain is True
    assert analyze.redact_name == ["Acme"]

    overridden = parser.parse_args(["analyze", "x.txt", "--provider", "gemini", "--no-redact", "--no-explain", "--perspective", "vendor"])
    assert overridden.provider == "gemini" and overridden.perspective == "vendor"
    assert overridden.redact is False and overridden.explain is False

    assert parser.parse_args(["batch", "folder"]).parallel == 4


def test_config_only_touches_commands_that_have_the_option():
    parser = build_parser()
    apply_config_defaults(parser, {"parallel": 5, "client": "Acme"})
    assert parser.parse_args(["providers"]).__dict__.get("parallel") is None
    assert parser.parse_args(["batch", "folder"]).client == "Acme"


def test_main_uses_config_file_end_to_end(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("provider: offline\nperspective: client\n", encoding="utf-8")
    old = {k: os.environ.get(k) for k in ("HERMES_LEGAL_CONFIG", "HERMES_LEGAL_HOME")}
    os.environ["HERMES_LEGAL_CONFIG"] = str(cfg)
    os.environ["HERMES_LEGAL_HOME"] = str(tmp_path)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["analyze", str(SAMPLE), "--format", "json", "--no-save"])
        data = json.loads(out.getvalue())
        assert data["provider"] == "offline"
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
