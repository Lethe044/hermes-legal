"""
Model Context Protocol (MCP) server.

`hermes-legal mcp` lets an AI assistant that supports MCP (Claude Desktop,
and other MCP clients) call contract analysis as a tool. It speaks the MCP
stdio transport: one JSON-RPC 2.0 message per line on stdin and stdout.

Built on the standard library only, so it adds no dependency.

Safety decisions, because an agent can be tricked by text inside a document
(prompt injection):

- Which provider is used, and whether privacy mode (redaction) is on, are
  decided by whoever starts the server, through command line flags. The
  agent cannot pick a remote provider or switch redaction off.
- Files can only be read from folders listed with --allow-dir. With none
  listed, only the current working directory is allowed.
- Results are not written to history unless the agent explicitly asks to
  save them.
- Nothing is ever printed to stdout except protocol messages.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import __version__
from .analysis.engine import analyze_contract
from .ask import ask_contract
from .clause_library import MODEL_CLAUSES
from .ingest import read_document
from .memory.store import MemoryStore
from .playbook import Playbook
from .providers import get_provider

SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
MAX_TEXT_CHARS = 500_000

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ToolError(Exception):
    """A problem the agent should see as a tool result, not as a protocol error."""


def _schema(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False}


_SOURCE_PROPS = {
    "path": {"type": "string", "description": "Path to a contract file (.txt, .md, .pdf, .docx) inside an allowed folder."},
    "text": {"type": "string", "description": "The contract text itself. Use this or 'path', not both."},
}

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "analyze_contract",
        "description": (
            "Analyze a contract for risk. Scores each clause 1-10, flags red flags, lists missing standard "
            "clauses, suggests redlines with model clause language, and returns an overall risk level and a "
            "SIGN / NEGOTIATE / REJECT verdict. Not legal advice."
        ),
        "inputSchema": _schema({
            **_SOURCE_PROPS,
            "perspective": {"type": "string", "description": "Whose side to review for: neutral, client, vendor, contractor, employer, employee, tenant, landlord.", "default": "neutral"},
            "client": {"type": "string", "description": "Optional client or matter name to tag the analysis with."},
            "explain": {"type": "boolean", "description": "Add plain-English explanations of each clause.", "default": False},
            "save": {"type": "boolean", "description": "Save this analysis to the history. Off by default.", "default": False},
        }),
    },
    {
        "name": "ask_contract",
        "description": "Ask a specific question about one contract, answered from that contract's own text.",
        "inputSchema": _schema({**_SOURCE_PROPS, "question": {"type": "string", "description": "The question to answer."}}, ["question"]),
    },
    {
        "name": "get_model_clause",
        "description": "Get a balanced starting-point replacement clause (for example Termination, Liability, Non-Compete). Call without a name to list the available clauses.",
        "inputSchema": _schema({"name": {"type": "string", "description": "Clause name. Omit to list all."}}),
    },
    {
        "name": "contract_history",
        "description": "List contracts analyzed and saved earlier: type, parties, risk level, verdict, client.",
        "inputSchema": _schema({
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            "client": {"type": "string", "description": "Only this client or matter."},
            "query": {"type": "string", "description": "Only entries containing this text."},
        }),
    },
    {
        "name": "list_deadlines",
        "description": "List contract terms, renewal windows and notice periods found in saved analyses, shortest first.",
        "inputSchema": _schema({"limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}}),
    },
]


class McpServer:
    def __init__(
        self,
        provider_name: str = "auto",
        allow_dirs: Optional[List[str]] = None,
        redact: bool = False,
        redact_names: Optional[List[str]] = None,
        memory: Optional[MemoryStore] = None,
        playbook: Optional[Playbook] = None,
    ):
        self.provider_name = provider_name
        dirs = allow_dirs or [os.getcwd()]
        self.allow_dirs = [Path(d).expanduser().resolve() for d in dirs]
        self.redact = redact
        self.redact_names = list(redact_names or [])
        self.memory = memory or MemoryStore()
        self.playbook = playbook or Playbook.load()
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {
            "analyze_contract": self._tool_analyze,
            "ask_contract": self._tool_ask,
            "get_model_clause": self._tool_model_clause,
            "contract_history": self._tool_history,
            "list_deadlines": self._tool_deadlines,
        }

    # ---------------- protocol ----------------

    def handle_message(self, message: Any) -> Optional[Any]:
        """Handle one decoded JSON-RPC message. Returns the response, or None for notifications."""
        if isinstance(message, list):
            responses = [r for r in (self.handle_message(m) for m in message) if r is not None]
            return responses or None
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
            return self._error(message.get("id") if isinstance(message, dict) else None, INVALID_REQUEST, "Invalid request")

        method = message["method"]
        msg_id = message.get("id")
        is_notification = "id" not in message
        params = message.get("params") or {}

        try:
            if method == "initialize":
                return self._result(msg_id, self._initialize(params))
            if method == "ping":
                return self._result(msg_id, {})
            if method == "tools/list":
                return self._result(msg_id, {"tools": TOOLS})
            if method == "tools/call":
                return self._result(msg_id, self._call_tool(params))
            if is_notification:
                return None  # notifications/initialized, notifications/cancelled, ...
            return self._error(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")
        except _InvalidParams as exc:
            return None if is_notification else self._error(msg_id, INVALID_PARAMS, str(exc))
        except Exception as exc:  # never let one bad request kill the server
            print(f"hermes-legal mcp: internal error: {exc!r}", file=sys.stderr)
            return None if is_notification else self._error(msg_id, INTERNAL_ERROR, "Internal error")

    @staticmethod
    def _result(msg_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
        return {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "hermes-legal", "version": __version__},
            "instructions": (
                "Contract risk analysis. Results are analysis, not legal advice: always tell the user to "
                "consult a qualified attorney before signing."
            ),
        }

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name not in self._handlers:
            raise _InvalidParams(f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise _InvalidParams("'arguments' must be an object")
        try:
            output = self._handlers[name](arguments)
            return {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}], "isError": False}
        except ToolError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except Exception as exc:
            print(f"hermes-legal mcp: tool {name} failed: {exc!r}", file=sys.stderr)
            return {"content": [{"type": "text", "text": f"The tool failed: {exc}"}], "isError": True}

    # ---------------- helpers ----------------

    def _load_text(self, args: Dict[str, Any]) -> str:
        path, text = args.get("path"), args.get("text")
        if bool(path) == bool(text):
            raise ToolError("Provide exactly one of 'path' or 'text'.")
        if text:
            if not isinstance(text, str):
                raise ToolError("'text' must be a string.")
            if len(text) > MAX_TEXT_CHARS:
                raise ToolError(f"The text is too long ({len(text)} characters, limit {MAX_TEXT_CHARS}).")
            return text
        if not isinstance(path, str):
            raise ToolError("'path' must be a string.")
        resolved = Path(path).expanduser().resolve()
        if not any(resolved == d or d in resolved.parents for d in self.allow_dirs):
            allowed = ", ".join(str(d) for d in self.allow_dirs)
            raise ToolError(
                f"That path is outside the allowed folders ({allowed}). "
                "The person running the server can allow more with --allow-dir."
            )
        try:
            content = read_document(resolved)
        except FileNotFoundError:
            raise ToolError(f"File not found: {path}")
        except Exception as exc:
            raise ToolError(f"Could not read the file: {exc}")
        if len(content) > MAX_TEXT_CHARS:
            raise ToolError(f"The document is too long ({len(content)} characters, limit {MAX_TEXT_CHARS}).")
        return content

    @staticmethod
    def _int(args: Dict[str, Any], key: str, default: int) -> int:
        value = args.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolError(f"'{key}' must be a whole number.")
        return max(1, min(value, 100))

    # ---------------- tools ----------------

    def _tool_analyze(self, args: Dict[str, Any]) -> Dict[str, Any]:
        text = self._load_text(args)
        perspective = args.get("perspective", "neutral")
        if not isinstance(perspective, str):
            raise ToolError("'perspective' must be a string.")
        outcome = analyze_contract(
            text,
            provider=get_provider(self.provider_name),
            perspective=perspective,
            memory=self.memory,
            playbook=self.playbook,
            explain=bool(args.get("explain", False)),
            save=bool(args.get("save", False)),
            client=args.get("client"),
            redact=self.redact,
            redact_names=self.redact_names,
        )
        data = outcome["result"].to_dict()
        data.update({
            "hash": outcome["hash"],
            "trend": outcome["trend"],
            "from_cache": outcome["from_cache"],
            "fallback_note": outcome["fallback_note"],
            "deadlines": outcome["obligations"],
            "disclaimer": "Analysis, not legal advice. Consult a qualified attorney before signing.",
        })
        return data

    def _tool_ask(self, args: Dict[str, Any]) -> Dict[str, Any]:
        question = args.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ToolError("'question' is required.")
        text = self._load_text(args)
        provider = get_provider(self.provider_name)
        answer = ask_contract(text, question, provider, redact=self.redact, redact_names=self.redact_names)
        return {"answer": answer, "provider": provider.name, "disclaimer": "Not legal advice."}

    def _tool_model_clause(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("name")
        if not name:
            return {"available": list(MODEL_CLAUSES)}
        match = next((n for n in MODEL_CLAUSES if n.lower() == str(name).lower()), None)
        if match is None:
            raise ToolError(f"No model clause named '{name}'. Available: {', '.join(MODEL_CLAUSES)}")
        return {"name": match, "clause": MODEL_CLAUSES[match], "note": "A starting-point template. Fill in the [BRACKETED] parts and adapt it."}

    def _tool_history(self, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = self._int(args, "limit", 20)
        entries = self.memory.contracts()
        if args.get("client"):
            entries = [c for c in entries if c.get("client") == args["client"]]
        if args.get("query"):
            q = str(args["query"]).lower()
            entries = [c for c in entries if q in json.dumps(c, ensure_ascii=False).lower()]
        keep = ("timestamp", "contract_type", "parties", "risk_level", "verdict", "client", "contract_hash", "perspective")
        return {"contracts": [{k: c.get(k) for k in keep} for c in entries[-limit:][::-1]]}

    def _tool_deadlines(self, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = self._int(args, "limit", 20)
        dated = [o for o in self.memory.all_obligations() if o.get("days") is not None]
        dated.sort(key=lambda o: o["days"])
        return {"obligations": dated[:limit], "note": "Durations are approximate and come from the contract text."}

    # ---------------- transport ----------------

    def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for raw in stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response: Any = self._error(None, PARSE_ERROR, "Parse error")
            else:
                response = self.handle_message(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
                stdout.flush()


class _InvalidParams(Exception):
    pass


def run_mcp_server(
    provider_name: str = "auto",
    allow_dirs: Optional[List[str]] = None,
    redact: bool = False,
    redact_names: Optional[List[str]] = None,
) -> None:
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    env_dirs = [d for d in os.environ.get("HERMES_LEGAL_MCP_ALLOW_DIRS", "").split(os.pathsep) if d]
    server = McpServer(
        provider_name=provider_name,
        allow_dirs=(allow_dirs or []) + env_dirs or None,
        redact=redact,
        redact_names=redact_names,
    )
    print(
        f"hermes-legal MCP server ready (provider: {provider_name}, folders: "
        f"{', '.join(str(d) for d in server.allow_dirs)}, privacy mode: {'on' if redact else 'off'})",
        file=sys.stderr,
    )
    server.serve()
