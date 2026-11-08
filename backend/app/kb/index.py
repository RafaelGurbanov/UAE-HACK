"""The searchable KB: chunks from kb/processed/*.jsonl, a Chroma collection for
dense vectors, and an in-memory BM25 index for exact terms and article numbers.

Reloads automatically when kb/processed changes (after `python -m app.kb.ingest`).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from app.core.config import get_settings
from app.kb.text import tokenize

log = logging.getLogger(__name__)
COLLECTION = "kb_chunks"


def chroma_client(index_dir: Path):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    index_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(index_dir), settings=ChromaSettings(anonymized_telemetry=False))


def get_collection(index_dir: Path, embedder_name: str | None = None, create: bool = True):
    client = chroma_client(index_dir)
    if create:
        meta = {"hnsw:space": "cosine"}
        if embedder_name:
            meta["embedder"] = embedder_name
        return client.get_or_create_collection(COLLECTION, metadata=meta)
    return client.get_collection(COLLECTION)


def chroma_meta(chunk: dict) -> dict:
    """Chroma metadata must be str/int/float/bool: no None, no lists."""
    keys = ["doc_id", "title", "article", "heading", "chapter", "layer", "status", "language", "url",
            "law_number", "issuing_body"]
    m = {k: ("" if chunk.get(k) is None else str(chunk[k])) for k in keys}
    m["year"] = int(chunk["year"]) if chunk.get("year") else 0
    m["part"] = int(chunk["part"]) if chunk.get("part") is not None else -1
    m["verified"] = bool(chunk.get("verified"))
    return m


def embed_text(chunk: dict) -> str:
    """Text that gets embedded: header path + body, so 'Article 7 of X' queries match."""
    path = " > ".join(x for x in [chunk.get("title"), chunk.get("chapter"),
                                  f"Article {chunk['article']}" if chunk.get("article") else chunk.get("heading")] if x)
    return f"{path}\n{chunk['text']}"


def load_chunks(processed_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    for f in sorted(processed_dir.glob("*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            chunks.extend(json.loads(line) for line in fh if line.strip())
    return chunks


class KBIndex:
    def __init__(self, kb_dir: Path, index_dir: Path):
        self.kb_dir, self.index_dir = kb_dir, index_dir
        self.processed = kb_dir / "processed"
        self._sig: tuple | None = None
        self._lock = threading.Lock()
        self.chunks: list[dict] = []
        self.by_id: dict[str, dict] = {}
        self.bm25 = None
        self._collection = None

    def _signature(self) -> tuple:
        files = sorted(self.processed.glob("*.jsonl"))
        return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in files)

    def ensure_loaded(self) -> None:
        sig = self._signature()
        if sig == self._sig:
            return
        with self._lock:
            if sig == self._sig:
                return
            from rank_bm25 import BM25Okapi

            self.chunks = load_chunks(self.processed)
            self.by_id = {c["chunk_id"]: c for c in self.chunks}
            corpus = [tokenize(embed_text(c)) for c in self.chunks]
            self.bm25 = BM25Okapi(corpus) if corpus else None
            self._collection = None
            self._sig = sig
            log.info("KB loaded: %d chunks from %d documents", len(self.chunks), len(sig))

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = get_collection(self.index_dir, create=False)
            except Exception:  # not ingested yet
                return None
        return self._collection

    def dense_count(self) -> int:
        col = self.collection
        return col.count() if col is not None else 0


_index: KBIndex | None = None


def get_index() -> KBIndex:
    global _index
    s = get_settings()
    if _index is None:
        _index = KBIndex(s.kb_dir, s.index_dir)
    _index.ensure_loaded()
    return _index
