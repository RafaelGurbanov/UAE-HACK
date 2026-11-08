"""Ingest every PDF / HTML / TXT / MD file in kb/raw into the knowledge base.

    python -m app.kb.ingest              # (re)index new or changed files
    python -m app.kb.ingest --reset      # wipe the index and rebuild everything
    python -m app.kb.ingest --doc <id>   # only one document

Metadata comes from kb/sources.csv (matched by `local_file`, else by doc_id = file name).
Files not in the CSV are auto-registered with status unknown, verified=false and
"SOURCE TO BE VERIFIED", so nothing enters the KB without showing up for review.
The layer is taken from the folder: kb/raw/<uae_federal|emirate|global_example>/...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
import time
from datetime import date
from pathlib import Path

from app.core.config import get_settings
from app.kb.chunking import SUPPORTED, chunk_document, parse_file
from app.kb.embeddings import get_embedder
from app.kb.index import chroma_meta, embed_text, get_collection
from app.kb.registry import LAYERS, append_row, read_rows, slugify
from app.kb.text import detect_language

log = logging.getLogger("ingest")


def _rel(path: Path, kb_dir: Path) -> str:
    return path.relative_to(kb_dir).as_posix()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def discover(kb_dir: Path) -> list[Path]:
    raw = kb_dir / "raw"
    return sorted(p for p in raw.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
                  and not p.name.startswith((".", "~")))


def match_rows(files: list[Path], kb_dir: Path) -> list[tuple[Path, dict, bool]]:
    rows = read_rows(kb_dir)
    by_file = {r.get("local_file", "").replace("\\", "/").strip(): r for r in rows if r.get("local_file")}
    by_id = {r["doc_id"]: r for r in rows}
    out = []
    for f in files:
        rel = _rel(f, kb_dir)
        row = by_file.get(rel) or by_file.get(rel.removeprefix("raw/")) or by_id.get(f.stem)
        out.append((f, row, row is None))
    return out


def auto_row(f: Path, kb_dir: Path, text: str, existing_ids: set[str]) -> dict:
    layer = f.parent.name if f.parent.name in LAYERS else "uae_federal"
    lang = detect_language(text[:5000])
    base = slugify(f.stem)
    doc_id = base if base not in existing_ids else f"{base}-{lang}"
    return {
        "doc_id": doc_id, "title": f.stem.replace("_", " ").replace("-", " ").strip(),
        "issuing_body": "SOURCE TO BE VERIFIED", "status": "unknown", "layer": layer, "language": lang,
        "url": "", "retrieved_at": date.today().isoformat(), "verified": "false",
        "local_file": _rel(f, kb_dir), "notes": "auto-registered by ingest; SOURCE TO BE VERIFIED",
    }


def build_chunks(row: dict, pieces: list[dict], sha: str) -> list[dict]:
    doc_id = row["doc_id"]
    out, seen = [], set()
    for i, p in enumerate(pieces):
        key = f"art-{p['article']}" if p["article"] else f"sec-{i + 1}"
        cid = f"{doc_id}:{key}" + (f":{p['part']}" if p.get("part") is not None else "")
        while cid in seen:  # duplicated article numbers (annexes etc.)
            cid += "b"
        seen.add(cid)
        out.append({
            "chunk_id": cid, "doc_id": doc_id, "title": row.get("title") or doc_id,
            "law_number": row.get("law_number") or None, "year": row.get("year") or None,
            "issuing_body": row.get("issuing_body") or None, "status": row.get("status") or "unknown",
            "layer": row.get("layer") or "uae_federal", "language": row.get("language") or "en",
            "url": row.get("url") or "", "verified": (row.get("verified", "").lower() in {"1", "true", "yes"}),
            "domains": row.get("domains") or "", "article": p["article"], "heading": p.get("heading"),
            "chapter": p.get("chapter"), "part": p.get("part"), "text": p["text"], "source_sha": sha,
        })
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="delete the index and processed chunks first")
    ap.add_argument("--doc", help="only ingest this doc_id")
    ap.add_argument("--force", action="store_true", help="re-embed even if the file is unchanged")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    s = get_settings()
    kb = s.kb_dir
    processed = kb / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    if args.reset:
        shutil.rmtree(s.index_dir, ignore_errors=True)
        for f in processed.glob("*.jsonl"):
            f.unlink()
        log.info("Index and processed chunks cleared")

    files = discover(kb)
    if not files:
        log.error("No documents found in %s. Put PDF/HTML/TXT files in kb/raw/<layer>/ first.", kb / "raw")
        return 1

    embedder = get_embedder()
    col = get_collection(s.index_dir, embedder.name)
    if (col.metadata or {}).get("embedder") not in (None, embedder.name):
        log.error("Index was built with %s but EMBEDDING_PROVIDER/MODEL is now %s. Run with --reset.",
                  col.metadata.get("embedder"), embedder.name)
        return 2

    existing_ids = {r["doc_id"] for r in read_rows(kb)}
    summary = []
    t0 = time.perf_counter()
    for f, row, is_new in match_rows(files, kb):
        try:
            text = parse_file(f)
        except Exception as e:
            log.error("%s: could not parse (%s)", f.name, e)
            summary.append((f.name, "-", 0, 0, f"parse error: {e}"))
            continue
        if is_new:
            row = auto_row(f, kb, text, existing_ids)
            existing_ids.add(row["doc_id"])
            append_row(kb, row)
            log.warning("%s: not in sources.csv; auto-registered as '%s' (verify title, status and URL)",
                        f.name, row["doc_id"])
        if args.doc and row["doc_id"] != args.doc:
            continue

        sha = _sha(f)
        out = processed / f"{row['doc_id']}.jsonl"
        if out.exists() and not args.force and not args.reset:
            first = out.read_text(encoding="utf-8").split("\n", 1)[0]
            if first and json.loads(first).get("source_sha") == sha:
                n = sum(1 for _ in out.open(encoding="utf-8"))
                summary.append((f.name, row["doc_id"], "unchanged", n, "skipped (unchanged)"))
                continue

        pieces, n_articles = chunk_document(text)
        if not pieces:
            summary.append((f.name, row["doc_id"], 0, 0, "no text extracted (scanned PDF needs OCR)"))
            continue
        chunks = build_chunks(row, pieces, sha)

        # replace this document's vectors
        try:
            col.delete(where={"doc_id": row["doc_id"]})
        except Exception:
            pass
        for i in range(0, len(chunks), 64):
            batch = chunks[i : i + 64]
            col.upsert(ids=[c["chunk_id"] for c in batch], embeddings=embedder.embed([embed_text(c) for c in batch]),
                       documents=[c["text"] for c in batch], metadatas=[chroma_meta(c) for c in batch])
        with out.open("w", encoding="utf-8") as fh:
            for c in chunks:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
        note = "article structure" if n_articles else "no articles detected: paragraph chunks"
        summary.append((f.name, row["doc_id"], n_articles, len(chunks), note))
        log.info("%s -> %s: %d chunks (%s)", f.name, row["doc_id"], len(chunks), note)

    total = sum(n for *_, n, _ in summary if isinstance(n, int))
    print("\nIngest summary")
    print(f"{'file':40} {'doc_id':34} {'articles':>9} {'chunks':>7}  note")
    for name, doc_id, arts, n, note in summary:
        print(f"{name[:40]:40} {str(doc_id)[:34]:34} {str(arts):>9} {n:>7}  {note}")
    print(f"\n{total} chunks in {len(summary)} files; {col.count()} vectors in the index "
          f"({embedder.name}); {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
