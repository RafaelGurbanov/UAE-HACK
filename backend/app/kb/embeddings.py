"""Embedding and reranking providers.

EMBEDDING_PROVIDER:
  sentence_transformers  BAAI/bge-m3 locally (default, multilingual AR+EN; ~2.3 GB download on first use)
  ollama                 `ollama pull bge-m3`, served by a local Ollama
  hash                   OFFLINE TESTS ONLY: character n-gram hashing, no semantics. Never for real use.
"""

from __future__ import annotations

import hashlib
import logging
import math
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import Settings, get_settings
from app.kb.text import normalize_for_match

log = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer

        log.info("Loading embedding model %s (first run downloads it)", model)
        self._m = SentenceTransformer(model)
        self.name = f"st:{model}"

    def embed(self, texts):
        return self._m.encode(texts, batch_size=16, normalize_embeddings=True, show_progress_bar=len(texts) > 64).tolist()


class OllamaEmbedder:
    def __init__(self, model: str, base_url: str):
        self._model, self._base = model, base_url.rstrip("/")
        self.name = f"ollama:{model}"

    def embed(self, texts):
        out: list[list[float]] = []
        with httpx.Client(timeout=120) as c:
            for i in range(0, len(texts), 32):
                r = c.post(f"{self._base}/api/embed", json={"model": self._model, "input": texts[i : i + 32]})
                r.raise_for_status()
                out.extend(r.json()["embeddings"])
        return [_l2(v) for v in out]


class HashEmbedder:
    """Deterministic character-n-gram hashing. For offline tests of the plumbing only."""

    name = "hash:test-only"

    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, texts):
        vecs = []
        for t in texts:
            v = [0.0] * self.dim
            s = f" {normalize_for_match(t)} "
            for n in (3, 4, 5):
                for i in range(len(s) - n + 1):
                    h = int.from_bytes(hashlib.blake2b(s[i : i + n].encode(), digest_size=4).digest(), "little")
                    v[h % self.dim] += 1.0
            vecs.append(_l2(v))
        return vecs


def _l2(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@lru_cache
def get_embedder() -> Embedder:
    s: Settings = get_settings()
    if s.embedding_provider == "sentence_transformers":
        return SentenceTransformerEmbedder(s.embedding_model)
    if s.embedding_provider == "ollama":
        return OllamaEmbedder(s.embedding_model, s.ollama_base_url)
    if s.embedding_provider == "hash":
        log.warning("EMBEDDING_PROVIDER=hash is for offline tests only: retrieval quality is not meaningful")
        return HashEmbedder()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER '{s.embedding_provider}'")


class Reranker:
    def __init__(self, model: str):
        from sentence_transformers import CrossEncoder

        log.info("Loading reranker %s (first run downloads it)", model)
        self._m = CrossEncoder(model, max_length=512)  # 1-label model -> sigmoid scores in [0, 1]

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        return [float(x) for x in self._m.predict([(query, p) for p in passages], batch_size=16)]


@lru_cache
def get_reranker() -> Reranker | None:
    s = get_settings()
    if not s.reranker_enabled or s.embedding_provider == "hash":
        return None
    return Reranker(s.reranker_model)
