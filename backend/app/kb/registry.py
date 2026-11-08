"""kb/sources.csv: the human-maintained list of every KB document.

Read by the API (/api/sources), and read+appended by ingest/add_source.
`verified=true` is set by a person after checking the file against the official source.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

from app.api.schemas import CoverageCell, SourceDocument

CSV_COLUMNS = [
    "doc_id", "title", "title_ar", "issuing_body", "law_number", "year", "status", "layer",
    "language", "translation_of", "amends", "domains", "url", "retrieved_at", "verified",
    "local_file", "notes",
]
LAYERS = {"uae_federal", "emirate", "global_example"}
STATUSES = {"in_force", "amended", "repealed", "not_legislation", "unknown"}


def _list(v: str | None) -> list[str]:
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def slugify(s: str, max_len: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:max_len].strip("-") or "doc"


def read_rows(kb_dir: Path) -> list[dict]:
    path = kb_dir / "sources.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("doc_id")]


def append_row(kb_dir: Path, row: dict) -> None:
    path = kb_dir / "sources.csv"
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in CSV_COLUMNS})


def _chunk_count(processed_dir: Path, doc_id: str) -> int:
    f = processed_dir / f"{doc_id}.jsonl"
    if not f.exists():
        return 0
    with f.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def row_to_document(row: dict, kb_dir: Path) -> SourceDocument:
    status = row.get("status") or "unknown"
    return SourceDocument(
        doc_id=row["doc_id"],
        title=row.get("title") or row["doc_id"],
        title_ar=row.get("title_ar") or None,
        issuing_body=row.get("issuing_body") or "SOURCE TO BE VERIFIED",
        law_number=row.get("law_number") or None,
        year=int(row["year"]) if (row.get("year") or "").isdigit() else None,
        status=status if status in STATUSES else "unknown",
        layer=row.get("layer") if row.get("layer") in LAYERS else "uae_federal",
        language="ar" if row.get("language") == "ar" else "en",
        translation_of=row.get("translation_of") or None,
        amends=_list(row.get("amends")),
        domains=[d for d in _list(row.get("domains"))],
        url=row.get("url") or "",
        retrieved_at=row.get("retrieved_at") or None,
        verified=(row.get("verified", "").lower() in {"1", "true", "yes"}),
        chunk_count=_chunk_count(kb_dir / "processed", row["doc_id"]),
    )


def load_sources(kb_dir: Path) -> list[SourceDocument]:
    docs = []
    for row in read_rows(kb_dir):
        try:
            docs.append(row_to_document(row, kb_dir))
        except Exception:  # a malformed row must not take the API down
            continue
    by_id = {d.doc_id: d for d in docs}
    for d in docs:
        for base in d.amends:
            if base in by_id:
                by_id[base].amended_by.append(d.doc_id)
    return docs


def coverage(docs: list[SourceDocument]) -> list[CoverageCell]:
    c: Counter = Counter()
    for d in docs:
        for dom in d.domains:
            c[(d.layer, dom)] += 1
    return [CoverageCell(layer=lay, domain=dom, documents=n) for (lay, dom), n in sorted(c.items())]
