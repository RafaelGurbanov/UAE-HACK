"""Run the question set through the LIVE pipeline and write a report.

    python -m app.kb.evaluate                       # kb/eval/questions.jsonl
    python -m app.kb.evaluate --questions my.jsonl  # one JSON object per line: {"id","question", ...}

Optional per-question fields: "expect_refusal": true, "expected": [{"doc_id": "...", "article": "7"}].
Writes kb/eval/report.md (human-readable) and kb/eval/report.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from app.agents import router as pipeline
from app.api.schemas import AskRequest
from app.core.config import get_settings
from app.kb.index import get_index


async def _one(q: dict) -> dict:
    t0 = time.perf_counter()
    rec = {"id": q.get("id"), "question": q["question"], "expect_refusal": q.get("expect_refusal")}
    retrieval = None
    try:
        async for ev, data in pipeline.run(AskRequest(question=q["question"])):
            if ev == "retrieval":
                retrieval = data
            elif ev == "final":
                rec["outcome"] = data["outcome"]
                rec["mode"] = data.get("mode")
                rec["matched_entry"] = data.get("matched_entry")
                rec["verification"] = data.get("verification")
                ans = data.get("answer") or {}
                rec["short_answer"] = ans.get("short_answer")
                rec["citations"] = [f"{c['doc_id']} art. {c.get('article') or '-'}" for c in ans.get("legal_basis", [])]
                rec["pipeline_nodes"] = data.get("pipeline_nodes")
                rec["audit_id"] = data.get("audit_id")
    except Exception as e:
        rec["outcome"] = "error"
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    rec["best_score"] = retrieval.get("best_score") if retrieval else None
    rec["threshold"] = retrieval.get("threshold") if retrieval else None
    rec["top_passages"] = [f"{c['doc_id']} art. {c.get('article') or '-'} ({c['score']})"
                           for c in (retrieval or {}).get("chunks", [])[:3]]
    exp = q.get("expected") or []
    if exp:
        got = {(c["doc_id"], str(c.get("article"))) for c in (retrieval or {}).get("chunks", [])}
        rec["retrieval_hit"] = any((e["doc_id"], str(e.get("article"))) in got for e in exp)
    if q.get("expect_refusal") is not None:
        rec["refusal_correct"] = (rec.get("outcome") == "no_source") == bool(q["expect_refusal"])
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    return rec


def _md(results: list[dict], index_chunks: int, docs: int) -> str:
    s = get_settings()
    n = len(results)
    answered = sum(r.get("outcome") == "answered" for r in results)
    refused = sum(r.get("outcome") == "no_source" for r in results)
    errors = sum(r.get("outcome") == "error" for r in results)
    passed = sum(bool((r.get("verification") or {}).get("passed")) for r in results if r.get("outcome") == "answered")
    lines = [
        "# Live evaluation report", "",
        f"- Knowledge base: {docs} documents, {index_chunks} chunks indexed",
        ("- Mode: OFFLINE (kb/data JSON + verbatim passages, no LLM calls)" if s.offline
         else f"- LLM: {s.effective_provider} / {s.llm_model} (router {s.llm_router_model})"),
        f"- Embeddings: {s.embedding_provider} / {s.embedding_model}; reranker: "
        f"{s.reranker_model if s.reranker_enabled else 'off'}",
        f"- Questions: {n}. Answered: {answered} (verification passed: {passed}). No source: {refused}. Errors: {errors}.",
    ]
    refusal = [r for r in results if "refusal_correct" in r]
    if refusal:
        lines.append(f"- Refusal behaviour correct: {sum(r['refusal_correct'] for r in refusal)}/{len(refusal)}")
    hits = [r for r in results if "retrieval_hit" in r]
    if hits:
        lines.append(f"- Retrieval hit rate (expected article in top {s.retrieval_top_k}): "
                     f"{sum(r['retrieval_hit'] for r in hits)}/{len(hits)}")
    lines += ["", "| # | Question | Outcome | Mode / entry | Verified | Best score | Citations / top passages | s |",
              "|---|---|---|---|---|---|---|---|"]
    for r in results:
        v = r.get("verification") or {}
        ver = f"{v.get('verified', 0)}/{v.get('checked', 0)}" + (" ✓" if v.get("passed") else "") if v else "-"
        cites = "; ".join(r.get("citations") or []) or "; ".join(r.get("top_passages") or []) or r.get("error", "")
        q = r["question"].replace("|", "/")
        lines.append(f"| {r.get('id')} | {q} | {r.get('outcome')} | {r.get('mode')} {r.get('matched_entry') or ''} | {ver} | {r.get('best_score')} | {cites[:160]} | "
                     f"{r.get('seconds')} |")
    lines += ["", "## Answers", ""]
    for r in results:
        lines.append(f"**{r.get('id')}. {r['question']}** ({r.get('outcome')})")
        if r.get("short_answer"):
            lines.append(f"> {r['short_answer']}")
        if (r.get("verification") or {}).get("removed"):
            lines.append(f"- Removed: {'; '.join(r['verification']['removed'])}")
        if r.get("error"):
            lines.append(f"- Error: {r['error']}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--questions", type=Path)
    a = ap.parse_args(argv)
    s = get_settings()
    qfile = a.questions or (s.kb_dir / "eval" / "questions.jsonl")
    if not qfile.exists():
        print(f"Question file not found: {qfile}", file=sys.stderr)
        return 1
    qs = [json.loads(line) for line in qfile.read_text(encoding="utf-8").splitlines() if line.strip()]
    idx = get_index()
    if not idx.chunks and not s.offline:
        print("Knowledge base is empty. Run: python -m app.kb.ingest", file=sys.stderr)
        return 1

    async def run_all():
        out = []
        for q in qs:
            print(f"[{q.get('id')}] {q['question'][:70]} ...", flush=True)
            r = await _one(q)
            print(f"      -> {r.get('outcome')} (best {r.get('best_score')}, {r.get('seconds')}s)", flush=True)
            out.append(r)
        return out

    results = asyncio.run(run_all())
    docs = len({c["doc_id"] for c in idx.chunks})
    out_dir = s.kb_dir / "eval"
    (out_dir / "report.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(_md(results, idx.dense_count() or len(idx.chunks), docs), encoding="utf-8")
    print(f"\nReport written to {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
