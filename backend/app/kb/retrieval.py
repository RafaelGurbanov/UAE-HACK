"""Hybrid retrieval: dense (Chroma) + BM25, fused with reciprocal-rank fusion,
then reranked with a cross-encoder. Repealed text and unrequested layers are
filtered out before ranking.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.kb.embeddings import get_embedder, get_reranker
from app.kb.index import KBIndex, embed_text
from app.kb.text import to_ascii_digits, tokenize

log = logging.getLogger(__name__)
RRF_K = 60


@dataclass
class Hit:
    chunk: dict
    score: float = 0.0            # the score used for the no_source decision
    dense: float | None = None    # best cosine similarity over all query variants
    bm25: float | None = None
    rerank: float | None = None
    rrf: float = 0.0
    sources: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    hits: list[Hit]
    best_score: float
    threshold: float
    score_kind: str  # "rerank" | "dense" | "bm25"
    queries: list[str]

    @property
    def supported(self) -> bool:
        return bool(self.hits) and self.best_score >= self.threshold


_ARTICLE_REF = re.compile(r"(?:article|art\.?|المادة|مادة)\s*\(?\s*([0-9٠-٩]+)", re.I)


def _allowed(chunk: dict, layers: set[str], include_repealed: bool) -> bool:
    if layers and chunk.get("layer") not in layers:
        return False
    return include_repealed or chunk.get("status") != "repealed"


def retrieve(index: KBIndex, question: str, queries: list[str], layers: list[str],
             include_repealed: bool = False, top_k: int | None = None) -> RetrievalResult:
    s = get_settings()
    top_k = top_k or s.retrieval_top_k
    layer_set = set(layers)
    queries = list(dict.fromkeys(q.strip() for q in [question, *queries] if q and q.strip()))[:6]
    hits: dict[str, Hit] = {}

    def hit(cid: str) -> Hit:
        if cid not in hits:
            hits[cid] = Hit(chunk=index.by_id[cid])
        return hits[cid]

    # ---- dense
    col = index.collection
    if col is not None and col.count() > 0:
        where: dict | None = None
        conds = []
        if layer_set:
            conds.append({"layer": {"$in": sorted(layer_set)}})
        if not include_repealed:
            conds.append({"status": {"$ne": "repealed"}})
        if conds:
            where = conds[0] if len(conds) == 1 else {"$and": conds}
        q_emb = get_embedder().embed(queries)
        n = min(25, col.count())
        res = col.query(query_embeddings=q_emb, n_results=n, where=where, include=["distances"])
        for ids, dists in zip(res["ids"], res["distances"], strict=True):
            for rank, (cid, dist) in enumerate(zip(ids, dists, strict=True)):
                if cid not in index.by_id:
                    continue
                h = hit(cid)
                sim = 1.0 - float(dist)
                h.dense = max(h.dense or -1.0, sim)
                h.rrf += 1.0 / (RRF_K + rank + 1)
                if "dense" not in h.sources:
                    h.sources.append("dense")

    # ---- BM25
    if index.bm25 is not None:
        for q in queries:
            toks = tokenize(q)
            if not toks:
                continue
            scores = index.bm25.get_scores(toks)
            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            rank = 0
            for i in order:
                if scores[i] <= 0 or rank >= 25:
                    break
                c = index.chunks[i]
                if not _allowed(c, layer_set, include_repealed):
                    continue
                h = hit(c["chunk_id"])
                h.bm25 = max(h.bm25 or 0.0, float(scores[i]))
                h.rrf += 1.0 / (RRF_K + rank + 1)
                if "bm25" not in h.sources:
                    h.sources.append("bm25")
                rank += 1

    # ---- explicit article reference ("Article 7", "المادة 7") gets a boost
    refs = {to_ascii_digits(m) for m in _ARTICLE_REF.findall(question)}
    ref_ids = {cid for cid, h in hits.items() if to_ascii_digits(str(h.chunk.get("article") or "")) in refs}
    for cid in ref_ids:
        hits[cid].rrf += 0.05

    cands = sorted(hits.values(), key=lambda h: h.rrf, reverse=True)[: s.retrieval_candidates]

    # ---- rerank
    reranker = get_reranker()
    if reranker and cands:
        scores = reranker.score(question, [embed_text(h.chunk)[:2000] for h in cands])
        for h, sc in zip(cands, scores, strict=True):
            h.rerank = sc
            h.score = sc
        cands.sort(key=lambda h: h.score, reverse=True)
        kind, threshold = "rerank", s.min_rerank_score
    elif any(h.dense is not None for h in cands):
        for h in cands:
            h.score = h.dense if h.dense is not None else 0.0
        cands.sort(key=lambda h: (h.score, h.rrf), reverse=True)
        kind, threshold = "dense", s.min_dense_score
    else:  # no vectors at all (index missing): BM25 only, conservative threshold
        for h in cands:
            h.score = min(1.0, (h.bm25 or 0.0) / 10.0)
        kind, threshold = "bm25", 0.3

    # an explicitly referenced article ("Article 7", "المادة 7") always ranks first
    cands.sort(key=lambda h: h.chunk["chunk_id"] not in ref_ids)
    top = cands[:top_k]
    best = top[0].score if top else 0.0
    return RetrievalResult(hits=top, best_score=best, threshold=threshold, score_kind=kind, queries=queries)
