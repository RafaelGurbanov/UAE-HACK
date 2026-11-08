"""Legal & Policy Adviser: the live /api/ask pipeline.

detect language -> rewrite/expand query (EN+AR, router model) -> hybrid retrieve
-> threshold (no_source, no LLM call) -> generate from numbered sources (stream)
-> verify citations -> tag nodes/dimensions -> audit log -> final response.

`run()` is an async generator of (event, data) pairs; the JSON endpoint keeps only
the final one, the SSE endpoint forwards them all. No canned answers anywhere.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator

from app.api.deps import get_audit
from app.api.schemas import (
    AnswerSections,
    AskRequest,
    AskResponse,
    Citation,
    RetrievedChunkRef,
    VerificationReport,
)
from app.core.config import get_settings
from app.core.taxonomy import AgentId, PipelineNode, ReadinessDimension
from app.kb.index import get_index
from app.kb.registry import load_sources
from app.kb.retrieval import RetrievalResult, retrieve
from app.kb.text import detect_language
from app.kb.verify import check, markers_in, parse_citations, strip_markers
from app.llm import LLMProvider, Message, get_llm

log = logging.getLogger(__name__)

NO_SOURCE = {
    "en": "No supporting source found in the knowledge base",
    "ar": "لم يُعثر على مصدر داعم في قاعدة المعرفة",
}
DISCLAIMER = {
    "en": "Informational only, not legal advice. The official Arabic text prevails.",
    "ar": "لأغراض المعلومات فقط وليست استشارة قانونية. يسود النص العربي الرسمي.",
}
GENERAL_LABEL = {
    "en": "Not from the knowledge base, not a legal source.",
    "ar": "ليست من قاعدة المعرفة وليست مصدراً قانونياً.",
}
DEFAULT_TOPICS = {
    "en": ["Children's data", "Consent", "In-app purchases", "Advertising to minors", "Cross-border transfer",
           "Counsellor review"],
    "ar": ["بيانات الأطفال", "الموافقة", "المشتريات داخل التطبيق", "الإعلان للقاصرين", "النقل عبر الحدود",
           "مراجعة المرشد"],
}
CHILD_WORDS = re.compile(r"\b(child|children|minor|minors|student|students|pupil|kid)s?\b|طفل|أطفال|قاصر|طالب|طلاب", re.I)

# ------------------------------------------------------------------ prompts
REWRITE_SYSTEM = """You turn a user's question about UAE law into search queries for a hybrid (keyword + semantic) search over legislation in Arabic and English.
Return ONLY a JSON object: {"en": [up to 3 English legal search queries], "ar": [up to 3 Arabic legal search queries], "keywords": [up to 6 exact legal terms]}.
Use formal legal vocabulary (e.g. "personal data of a child", "parental consent", "processing", "data subject"; "البيانات الشخصية", "موافقة ولي الأمر"). Keep any article or law numbers the user wrote. Do not answer the question."""

ANSWER_SYSTEM = """You are the Legal & Policy Adviser of the Qalam Policy Command Centre, a governance platform for a smart-pen service that screens middle-school students' handwriting for signs of learning difficulties (counsellor review is mandatory before anything reaches parents).

RULES (strict):
1. Answer ONLY from the numbered SOURCES in the user message. Do not use outside knowledge.
2. Never state a law name, law number, article number, date, penalty or obligation unless it appears in a SOURCE.
3. Every factual sentence in <short_answer> and <details> ends with a citation marker like [c1]. Each marker is defined in <citations>.
4. Each citation line is exactly: [cN] S<k> | <exact quote>. The quote is copied VERBATIM from source S<k> (10-40 words, same language as the source, no ellipsis, no paraphrase). One citation = one source; never merge two sources.
5. If the SOURCES do not answer the question, write that in <short_answer> and leave <citations> empty. Do not guess.
6. Note when a source is a translation; the official Arabic text prevails. Flag sources marked repealed or unverified in <status_and_limits>.
7. Write in {lang_name}. Plain prose, no markdown headings.

OUTPUT FORMAT (exactly these tags, in this order):
<short_answer>2-4 sentences with [cN] markers.</short_answer>
<details>Conditions, exceptions, penalties or procedures, ONLY if present in the sources, with [cN] markers. Empty if none.</details>
<status_and_limits>In-force status as given by the sources, what the sources do NOT cover.</status_and_limits>
<related>One related topic or provision per line, only from the sources. Empty if none.</related>
<citations>
[c1] S1 | exact quote
</citations>
<tags>nodes: comma-separated subset of SRC,C,PP,M,P,D,SINK affected (SRC=pen, C=school edge, PP=pre-processing, M=models, P=counsellor review, D=provider cloud, SINK=parent/teacher app)
dimensions: comma-separated subset of open_data_open_source, generative_ai_content_ecosystem, contextualisation_regional_development, domain_integration_cross_domain, human_interaction_supervision, ai_policy_implementation, ai_social_inclusion, digital_infrastructure_energy
child_affected: yes|no</tags>"""

GENERAL_SYSTEM = """You are a general AI assistant inside a UAE legal-policy demo. This answer is NOT grounded in the platform's knowledge base and is NOT a legal source.
Answer helpfully and concisely in {lang_name} (max ~180 words). Do not invent article numbers, law numbers or dates; if you are unsure about a specific legal provision, say so and suggest checking the official UAE legislation. Plain prose, no markdown headings."""

# ------------------------------------------------------------------ conversation memory (per process)
_CONV: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()


def _remember(cid: str, q: str, a: str) -> None:
    _CONV.setdefault(cid, []).append((q, a))
    _CONV[cid] = _CONV[cid][-3:]
    _CONV.move_to_end(cid)
    while len(_CONV) > 500:
        _CONV.popitem(last=False)


def _history(cid: str) -> str:
    turns = _CONV.get(cid) or []
    return "\n".join(f"Earlier question: {q}\nEarlier answer: {a}" for q, a in turns)


# ------------------------------------------------------------------ helpers
def _tag(text: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)(?:</{name}>|$)", text, re.S)
    return m.group(1).strip() if m else ""


def _enum_list(raw: str, enum) -> list:
    vals = {e.value for e in enum}
    return [enum(x) for x in dict.fromkeys(p.strip() for p in re.split(r"[,\s]+", raw)) if x in vals] if raw else []


async def _rewrite(llm: LLMProvider, question: str, history: str) -> tuple[list[str], dict]:
    s = get_settings()
    prompt = (f"{history}\n\n" if history else "") + f"Question: {question}"
    try:
        res = await llm.complete([Message("user", prompt)], system=REWRITE_SYSTEM, model=s.llm_router_model,
                                 max_tokens=400, json_mode=True)
        m = re.search(r"\{.*\}", res.text, re.S)
        data = json.loads(m.group(0)) if m else {}
        queries = [*data.get("en", [])[:3], *data.get("ar", [])[:3]]
        kw = " ".join(data.get("keywords", [])[:6])
        if kw:
            queries.append(kw)
        return [q for q in queries if isinstance(q, str)], {"model": res.model, "input_tokens": res.input_tokens,
                                                            "output_tokens": res.output_tokens}
    except Exception as e:  # rewrite is an optimisation; retrieval still runs on the raw question
        log.warning("query rewrite failed: %s", e)
        return [], {"error": str(e)[:200]}


def _sources_block(r: RetrievalResult, docs: dict) -> str:
    out = []
    for i, h in enumerate(r.hits, 1):
        c = h.chunk
        d = docs.get(c["doc_id"])
        flags = []
        if c.get("status") == "repealed":
            flags.append("REPEALED")
        if d is not None and not d.verified:
            flags.append("UNVERIFIED SOURCE")
        if d is not None and d.translation_of:
            flags.append("TRANSLATION")
        head = (f"S{i} | {c.get('title')} | "
                + (f"Law no. {c['law_number']} | " if c.get("law_number") else "")
                + (f"Year {c['year']} | " if c.get("year") else "")
                + (f"Article {c['article']}" if c.get("article") else (c.get("heading") or ""))
                + f" | layer={c.get('layer')} | status={c.get('status')} | lang={c.get('language')}"
                + (f" | {' '.join(flags)}" if flags else ""))
        out.append(f"{head}\n{c['text']}")
    return "\n\n---\n\n".join(out)


class _TagStreamer:
    """Emits only the text inside <short_answer>…</short_answer> while the model streams."""

    def __init__(self):
        self.buf, self.emitted, self.open, self.closed = "", 0, False, False

    def feed(self, delta: str) -> str:
        self.buf += delta
        if self.closed:
            return ""
        if not self.open:
            i = self.buf.find("<short_answer>")
            if i < 0:
                return ""
            self.open, self.emitted = True, i + len("<short_answer>")
        end = self.buf.find("</short_answer>", self.emitted)
        if end >= 0:
            out, self.emitted, self.closed = self.buf[self.emitted:end], end, True
            return out
        safe = len(self.buf) - len("</short_answer>")  # hold back a possible partial closing tag
        if safe > self.emitted:
            out, self.emitted = self.buf[self.emitted:safe], safe
            return out
        return ""


# ------------------------------------------------------------------ main pipeline
async def run(req: AskRequest) -> AsyncIterator[tuple[str, dict]]:
    s = get_settings()
    t0 = time.perf_counter()
    lang = req.language or detect_language(req.question)
    lang_name = "Arabic" if lang == "ar" else "English"
    conv_id = req.conversation_id or f"conv_{uuid.uuid4().hex[:10]}"
    answer_id = f"ans_{uuid.uuid4().hex[:10]}"
    steps: list[str] = [f"Language detected: {lang}"]
    audit = get_audit()
    llm = get_llm()  # raises RuntimeError if the provider is not configured

    # ---------------- general mode: plain AI answer, explicitly not grounded
    if req.mode == "general":
        text = ""
        async for delta in llm.stream([Message("user", req.question)], system=GENERAL_SYSTEM.format(lang_name=lang_name),
                                      max_tokens=600):
            text += delta
            yield "token", {"text": delta}
        entry = audit.log(kind="ask", mode="general", outcome="general", agent=AgentId.LEGAL_ADVISER,
                          input_event=req.question, reasoning_steps=[*steps, "Mode general: no retrieval, no citations"],
                          recommendation=text[:500], llm={"provider": llm.name, "model": s.llm_model,
                                                          "latency_ms": int((time.perf_counter() - t0) * 1000)})
        yield "final", AskResponse(
            answer_id=answer_id, conversation_id=conv_id, outcome="general", mode="general", language=lang,
            answer=AnswerSections(short_answer=text.strip(), legal_basis=[], details=None,
                                  status_and_limits=GENERAL_LABEL[lang], related=[], disclaimer=DISCLAIMER[lang]),
            audit_id=entry.audit_id,
        ).model_dump(mode="json")
        return

    # ---------------- grounded mode
    index = get_index()
    if not index.chunks:
        raise KBEmptyError("The knowledge base is empty. Put documents in kb/raw and run: python -m app.kb.ingest")

    history = _history(conv_id)
    rewrites, rw_usage = await _rewrite(llm, req.question, history)
    steps.append(f"Query variants: {len(rewrites)} ({'; '.join(rewrites[:6])[:300]})" if rewrites
                 else "Query rewrite unavailable; searching the raw question")

    layers = [x.value for x in req.filters.layers]
    r = retrieve(index, req.question, rewrites, layers, req.filters.include_repealed)
    steps.append(f"Retrieved {len(r.hits)} passages; best {r.score_kind} score {r.best_score:.3f} "
                 f"(threshold {r.threshold:.2f})")
    yield "retrieval", {"chunks": [{"chunk_id": h.chunk["chunk_id"], "doc_id": h.chunk["doc_id"],
                                    "article": h.chunk.get("article"), "score": round(h.score, 4)} for h in r.hits],
                        "best_score": round(r.best_score, 4), "threshold": r.threshold}
    refs = [RetrievedChunkRef(chunk_id=h.chunk["chunk_id"], doc_id=h.chunk["doc_id"], article=h.chunk.get("article"),
                              url=h.chunk.get("url") or "", score=round(h.score, 4)) for h in r.hits]

    def no_source(reason: str, verification: VerificationReport | None = None) -> dict:
        steps.append(f"Refused: {reason}")
        e = audit.log(kind="ask", mode="grounded", outcome="no_source", agent=AgentId.LEGAL_ADVISER,
                      input_event=req.question, retrieved_chunks=refs, reasoning_steps=steps,
                      llm={"provider": llm.name, "rewrite": rw_usage, "latency_ms": int((time.perf_counter() - t0) * 1000)})
        topics = list(dict.fromkeys(h.chunk.get("heading") or h.chunk.get("title") for h in r.hits[:3] if h.chunk))
        return AskResponse(
            answer_id=answer_id, conversation_id=conv_id, outcome="no_source", mode="grounded", language=lang,
            no_source_message=NO_SOURCE[lang],
            suggested_topics=[t for t in topics if t][:3] or DEFAULT_TOPICS[lang][:3],
            verification=verification, audit_id=e.audit_id,
        ).model_dump(mode="json")

    if not r.supported:
        yield "final", no_source(f"best score {r.best_score:.3f} below threshold {r.threshold:.2f}")
        return

    # ---------------- generate
    docs = {d.doc_id: d for d in load_sources(s.kb_dir)}
    user = (f"{history}\n\n" if history else "") + f"SOURCES:\n\n{_sources_block(r, docs)}\n\nQUESTION: {req.question}"
    streamer, full, usage = _TagStreamer(), "", {}
    t_gen = time.perf_counter()
    async for delta in llm.stream([Message("user", user)], system=ANSWER_SYSTEM.replace("{lang_name}", lang_name),
                                  max_tokens=s.llm_max_tokens):
        full += delta
        out = streamer.feed(delta)
        if out:
            yield "token", {"text": out}
    usage = {"provider": llm.name, "model": s.llm_model, "rewrite": rw_usage,
             "generation_ms": int((time.perf_counter() - t_gen) * 1000)}

    # ---------------- parse + verify
    short = _tag(full, "short_answer")
    details = _tag(full, "details")
    limits = _tag(full, "status_and_limits")
    related = [ln.strip("-•* ").strip() for ln in _tag(full, "related").splitlines() if ln.strip("-•* ").strip()]
    raw_cits = parse_citations(_tag(full, "citations"))
    tags = _tag(full, "tags")
    checked = check(raw_cits, [(h.chunk, h.score) for h in r.hits])
    ok = {c.raw.cid for c in checked if c.verified}
    failed = [c.reason for c in checked if not c.verified and c.reason]
    used = markers_in(short) | markers_in(details)
    undefined = sorted(used - {c.raw.cid for c in checked})
    short, rm1 = strip_markers(short, ok)
    details, rm2 = strip_markers(details, ok)
    warnings = [f"{m}: marker without a citation line" for m in undefined]
    # keep only verified citations that are actually referenced (or all verified if none referenced)
    referenced = [c for c in checked if c.verified and (c.raw.cid in used or not used)]
    vrep = VerificationReport(
        passed=bool(referenced) and not failed and not undefined,
        checked=len(checked), verified=len(ok), removed=failed, warnings=warnings,
    )
    steps.append(f"Citations: {len(checked)} emitted, {len(ok)} verified, {len(failed)} removed")
    yield "verification", vrep.model_dump(mode="json")

    if not referenced:
        yield "final", no_source("no citation could be verified against the retrieved text", vrep)
        return

    legal_basis = []
    for c in referenced:
        ch = c.chunk
        legal_basis.append(Citation(
            id=c.raw.cid, chunk_id=ch["chunk_id"], doc_id=ch["doc_id"], title=ch.get("title") or ch["doc_id"],
            law_number=ch.get("law_number") or None, year=int(ch["year"]) if ch.get("year") else None,
            article=ch.get("article"), clause=None, quote=c.raw.quote, url=ch.get("url") or "",
            layer=ch.get("layer") or "uae_federal", status=ch.get("status") or "unknown",
            language=ch.get("language") or "en", score=round(c.score, 4), verified=True,
        ))

    # system-added facts about the cited sources (not model claims)
    sys_notes = []
    unverified = sorted({c.doc_id for c in legal_basis if c.doc_id in docs and not docs[c.doc_id].verified})
    if unverified:
        sys_notes.append(("Registered but not yet human-verified source(s): " if lang == "en"
                          else "مصادر مسجلة لم يتم التحقق منها بشرياً بعد: ") + ", ".join(unverified))
    if failed:
        sys_notes.append(("Removed as unverifiable: " if lang == "en" else "أُزيل لتعذر التحقق: ") + "; ".join(failed))
    limits = " ".join([limits, *sys_notes]).strip()

    nodes = _enum_list(re.search(r"nodes:\s*(.*)", tags).group(1) if "nodes:" in tags else "", PipelineNode)
    dims = _enum_list(re.search(r"dimensions:\s*(.*)", tags).group(1) if "dimensions:" in tags else "",
                      ReadinessDimension)
    child = "child_affected: yes" in tags.lower() or bool(CHILD_WORDS.search(req.question))

    entry = audit.log(
        kind="ask", mode="grounded", outcome="answered", agent=AgentId.LEGAL_ADVISER, input_event=req.question,
        retrieved_chunks=refs, reasoning_steps=steps, recommendation=short[:500],
        citations=[c.chunk_id for c in legal_basis], confidence=round(r.best_score, 4),
        pipeline_nodes=nodes, readiness_dimensions=dims, requires_human_decision=child,
        llm={**usage, "latency_ms": int((time.perf_counter() - t0) * 1000)},
    )
    _remember(conv_id, req.question, short)
    yield "final", AskResponse(
        answer_id=answer_id, conversation_id=conv_id, outcome="answered", mode="grounded", language=lang,
        answer=AnswerSections(short_answer=short, legal_basis=legal_basis, details=details or None,
                              status_and_limits=limits or "-", related=related[:6], disclaimer=DISCLAIMER[lang]),
        pipeline_nodes=nodes, readiness_dimensions=dims, verification=vrep, requires_human_decision=child,
        audit_id=entry.audit_id,
    ).model_dump(mode="json")


class KBEmptyError(RuntimeError):
    pass
