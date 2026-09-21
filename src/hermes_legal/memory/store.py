"""Lightweight JSONL-backed memory of every contract ever analyzed.

No database, no server - just an append-only file under the user's home
directory. Simple, portable, and easy to inspect or back up.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryStore:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is not None:
            self.base_dir = base_dir
        elif os.environ.get("HERMES_LEGAL_HOME"):
            self.base_dir = Path(os.environ["HERMES_LEGAL_HOME"])
        else:
            self.base_dir = Path.home() / ".hermes-legal"
        self.reports_dir = self.base_dir / "reports"
        self.memory_file = self.base_dir / "contracts_memory.jsonl"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def write(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        entry.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def all_entries(self) -> List[Dict[str, Any]]:
        if not self.memory_file.exists():
            return []
        entries = []
        with open(self.memory_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def contracts(self) -> List[Dict[str, Any]]:
        return [e for e in self.all_entries() if e.get("type") == "contract_analyzed"]

    def find_by_hash(self, contract_hash: str) -> Optional[Dict[str, Any]]:
        matches = [c for c in self.contracts() if c.get("contract_hash") == contract_hash and c.get("full_result")]
        return matches[-1] if matches else None

    def find_by_client(self, client: str) -> List[Dict[str, Any]]:
        return [c for c in self.contracts() if c.get("client") == client]

    def clients(self) -> List[str]:
        seen = []
        for c in self.contracts():
            client = c.get("client")
            if client and client not in seen:
                seen.append(client)
        return seen

    def all_obligations(self) -> List[Dict[str, Any]]:
        """Flatten every contract's extracted obligations into one list, each
        tagged with which contract and when it was analyzed."""
        out = []
        for c in self.contracts():
            for ob in c.get("obligations", []) or []:
                out.append({
                    **ob,
                    "contract_type": c.get("contract_type"),
                    "parties": c.get("parties"),
                    "analyzed_at": c.get("timestamp"),
                    "contract_hash": c.get("contract_hash"),
                })
        return out

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        q = query.lower()
        matches = [e for e in self.all_entries() if q in json.dumps(e, ensure_ascii=False).lower()]
        return matches[-limit:]

    def find_by_party(self, party: str) -> List[Dict[str, Any]]:
        q = party.lower()
        return [c for c in self.contracts() if q in c.get("parties", "").lower()]
