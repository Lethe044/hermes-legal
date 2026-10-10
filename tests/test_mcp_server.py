import io
import json
import os
import subprocess
import sys
import types
from pathlib import Path

from hermes_legal.mcp_server import MAX_TEXT_CHARS, TOOLS, McpServer
from hermes_legal.memory.store import MemoryStore
from hermes_legal.playbook import Playbook

SAMPLES = Path(__file__).parent.parent / "sample_contracts"
FREELANCE = (SAMPLES / "freelance_contract.txt").read_text(encoding="utf-8")


def make_server(tmp_path, **kwargs):
    kwargs.setdefault("provider_name", "offline")
    kwargs.setdefault("allow_dirs", [str(SAMPLES)])
    return McpServer(memory=MemoryStore(base_dir=tmp_path), playbook=Playbook(), **kwargs)


def call(server, name, arguments=None, msg_id=1):
    reply = server.handle_message(
        {"jsonrpc": "2.0", "id": msg_id, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}}
    )
    result = reply["result"]
    text = result["content"][0]["text"]
    return result["isError"], (text if result["isError"] else json.loads(text))


def test_initialize_echoes_supported_version_and_falls_back_for_unknown(tmp_path):
    s = make_server(tmp_path)
    ok = s.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
    assert ok["result"]["protocolVersion"] == "2024-11-05"
    assert ok["result"]["serverInfo"]["name"] == "hermes-legal"
    assert "tools" in ok["result"]["capabilities"]
    odd = s.handle_message({"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
    assert odd["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_response_and_ping_works(tmp_path):
    s = make_server(tmp_path)
    assert s.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert s.handle_message({"jsonrpc": "2.0", "id": 3, "method": "ping"})["result"] == {}


def test_tools_list_exposes_five_documented_tools(tmp_path):
    s = make_server(tmp_path)
    tools = s.handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    assert [t["name"] for t in tools] == [
        "analyze_contract", "ask_contract", "get_model_clause", "contract_history", "list_deadlines",
    ]
    for t in tools:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"


def test_agent_cannot_choose_provider_or_switch_off_redaction():
    forbidden = {"provider", "redact", "redact_names", "redact_name", "no_redact"}
    for tool in TOOLS:
        assert forbidden.isdisjoint(tool["inputSchema"]["properties"]), tool["name"]


def test_unknown_method_and_unknown_tool_and_invalid_request(tmp_path):
    s = make_server(tmp_path)
    assert s.handle_message({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})["error"]["code"] == -32601
    bad = s.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "nope"}})
    assert bad["error"]["code"] == -32602
    assert s.handle_message({"id": 3})["error"]["code"] == -32600


def test_analyze_by_path_inside_allowed_folder(tmp_path):
    is_error, data = call(make_server(tmp_path), "analyze_contract", {"path": str(SAMPLES / "freelance_contract.txt")})
    assert not is_error
    assert data["parties"] == "TechCorp Inc. and Contractor"
    assert data["overall_risk"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert "disclaimer" in data and "deadlines" in data


def test_analyze_by_text_and_perspective(tmp_path):
    is_error, data = call(make_server(tmp_path), "analyze_contract", {"text": FREELANCE, "perspective": "client"})
    assert not is_error and data["clauses"]


def test_path_outside_allowed_folders_is_refused(tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("private notes", encoding="utf-8")
    is_error, message = call(make_server(tmp_path), "analyze_contract", {"path": str(outside)})
    assert is_error and "outside the allowed folders" in message


def test_path_traversal_is_refused(tmp_path):
    sneaky = str(SAMPLES / ".." / ".." / "pyproject.toml")
    is_error, message = call(make_server(tmp_path), "analyze_contract", {"path": sneaky})
    assert is_error


def test_default_allowed_folder_is_current_directory(tmp_path):
    s = McpServer(provider_name="offline", memory=MemoryStore(base_dir=tmp_path), playbook=Playbook())
    assert s.allow_dirs == [Path(os.getcwd()).resolve()]


def test_source_must_be_exactly_one_of_path_or_text(tmp_path):
    s = make_server(tmp_path)
    assert call(s, "analyze_contract", {})[0]
    assert call(s, "analyze_contract", {"path": str(SAMPLES / "nda_contract.txt"), "text": "x"})[0]


def test_oversized_text_is_refused(tmp_path):
    is_error, message = call(make_server(tmp_path), "analyze_contract", {"text": "a" * (MAX_TEXT_CHARS + 1)})
    assert is_error and "too long" in message


def test_missing_file_is_a_tool_error_not_a_crash(tmp_path):
    is_error, message = call(make_server(tmp_path), "analyze_contract", {"path": str(SAMPLES / "missing.txt")})
    assert is_error and "not found" in message.lower()


def test_analysis_is_not_saved_unless_asked(tmp_path):
    s = make_server(tmp_path)
    call(s, "analyze_contract", {"text": FREELANCE})
    assert s.memory.contracts() == []
    call(s, "analyze_contract", {"text": FREELANCE, "save": True, "client": "Acme"})
    assert len(s.memory.contracts()) == 1
    assert s.memory.contracts()[0]["client"] == "Acme"


def test_history_and_deadlines_read_saved_analyses(tmp_path):
    s = make_server(tmp_path)
    call(s, "analyze_contract", {"text": FREELANCE, "save": True, "client": "Acme"})
    _, history = call(s, "contract_history", {"client": "Acme"})
    assert len(history["contracts"]) == 1
    assert "full_result" not in history["contracts"][0]
    _, none = call(s, "contract_history", {"client": "Nobody"})
    assert none["contracts"] == []
    _, deadlines = call(s, "list_deadlines", {})
    assert "obligations" in deadlines
    assert call(s, "contract_history", {"limit": "ten"})[0]


def test_ask_contract_offline_answers_from_the_text(tmp_path):
    is_error, data = call(make_server(tmp_path), "ask_contract", {"text": FREELANCE, "question": "payment terms"})
    assert not is_error and "answer" in data
    assert call(make_server(tmp_path), "ask_contract", {"text": FREELANCE})[0]


def test_model_clause_tool(tmp_path):
    s = make_server(tmp_path)
    _, listing = call(s, "get_model_clause", {})
    assert "Termination" in listing["available"]
    _, one = call(s, "get_model_clause", {"name": "liability"})
    assert one["name"] == "Liability" and "liability" in one["clause"].lower()
    assert call(s, "get_model_clause", {"name": "Nonexistent"})[0]


def test_privacy_mode_is_enforced_by_the_server_not_the_agent(tmp_path):
    seen = {}

    class FakeGroq:
        def __init__(self, api_key=None):
            def create(**kwargs):
                seen["prompt"] = kwargs["messages"][-1]["content"]
                message = types.SimpleNamespace(content="not json")
                return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

            self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=create))

    module = types.ModuleType("groq")
    module.Groq = FakeGroq
    previous = sys.modules.get("groq")
    sys.modules["groq"] = module
    old_key = os.environ.get("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = "test-key"
    try:
        server = make_server(tmp_path, provider_name="groq", redact=True, redact_names=["TechCorp"])
        text = FREELANCE + "\nContact legal@techcorp.example.com"
        call(server, "analyze_contract", {"text": text})
    finally:
        if previous is None:
            sys.modules.pop("groq", None)
        else:
            sys.modules["groq"] = previous
        if old_key is None:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = old_key
    assert "legal@techcorp.example.com" not in seen["prompt"]
    assert "TechCorp" not in seen["prompt"]


def test_serve_handles_lines_blank_lines_and_garbage(tmp_path):
    s = make_server(tmp_path)
    lines = "\n".join([
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
        "",
        "this is not json",
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    ]) + "\n"
    out = io.StringIO()
    s.serve(io.StringIO(lines), out)
    replies = [json.loads(l) for l in out.getvalue().splitlines()]
    assert [r.get("id") for r in replies] == [1, None, 2]
    assert replies[1]["error"]["code"] == -32700


def test_real_stdio_session_in_a_subprocess(tmp_path):
    env = dict(os.environ, HERMES_LEGAL_HOME=str(tmp_path))
    proc = subprocess.Popen(
        [sys.executable, "-m", "hermes_legal.cli", "mcp", "--provider", "offline", "--allow-dir", str(SAMPLES)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    try:
        def rpc(msg):
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
            return json.loads(proc.stdout.readline())

        assert rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})["result"]["serverInfo"]["name"] == "hermes-legal"
        reply = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                     "params": {"name": "analyze_contract", "arguments": {"path": str(SAMPLES / "nda_contract.txt")}}})
        data = json.loads(reply["result"]["content"][0]["text"])
        assert data["parties"] == "Alpha Ventures LLC and Beta Solutions Ltd"
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)
    assert proc.returncode == 0
