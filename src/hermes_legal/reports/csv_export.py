from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List


def write_batch_csv(rows: List[Dict[str, Any]], out_path: str | Path) -> Path:
    """
    Write a one-row-per-contract CSV summary, used by batch mode so a
    whole folder of contracts can be triaged at a glance in a spreadsheet.
    """
    out_path = Path(out_path)
    fieldnames = [
        "file", "contract_type", "parties", "language", "overall_risk",
        "verdict", "red_flag_count", "clause_count", "provider", "hash",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return out_path
