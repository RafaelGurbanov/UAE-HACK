"""Append-only JSONL audit log. One line per agent call / decision.

JSONL is greppable, diffable, trivially exportable, and survives crashes
mid-run. Good enough for a hackathon; swap for SQLite if filtering gets slow.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.api.schemas import AuditEntry


def new_audit_id() -> str:
    return f"aud_{uuid.uuid4().hex[:12]}"


class AuditLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, entry: AuditEntry) -> AuditEntry:
        line = entry.model_dump_json()
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return entry

    def log(self, **fields) -> AuditEntry:
        fields.setdefault("audit_id", new_audit_id())
        fields.setdefault("timestamp", datetime.now(UTC))
        return self.write(AuditEntry(**fields))

    def read(self, *, agent: str | None = None, run_id: str | None = None, kind: str | None = None,
             since: datetime | None = None, limit: int | None = None, node: str | None = None,
             requires_human: bool | None = None, outcome: str | None = None) -> list[AuditEntry]:
        if not self.path.exists():
            return []
        out: list[AuditEntry] = []
        with self.path.open(encoding="utf-8") as f:
            for raw in f:
                if not raw.strip():
                    continue
                e = AuditEntry.model_validate(json.loads(raw))
                if agent and (e.agent is None or e.agent.value != agent):
                    continue
                if run_id and e.run_id != run_id:
                    continue
                if kind and e.kind != kind:
                    continue
                if since and e.timestamp < since:
                    continue
                if node and node not in [n.value for n in e.pipeline_nodes]:
                    continue
                if requires_human is not None and e.requires_human_decision != requires_human:
                    continue
                if outcome and e.outcome != outcome:
                    continue
                out.append(e)
        out.sort(key=lambda e: e.timestamp, reverse=True)
        return out[:limit] if limit else out

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open(encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
