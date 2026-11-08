"""Offline JSON mode: FREE, local, no LLM calls anywhere in this module.

Order of decisions for a question:
1. guidance    : greetings / small talk / empty questions get a short how-to message.
2. offline_json: best kb/data entry by hybrid score (weighted term coverage, BM25 tie-break,
                 + bge-m3 similarity when the model is already on disk) >= OFFLINE_MIN_SCORE.
3. extractive  : otherwise, if ingested documents (kb/processed) hold a strong passage match
                 (>= EXTRACTIVE_MIN_SCORE), return 1-3 passages VERBATIM.
4. no_source   : "No supporting source found in the knowledge base" + suggested topics.
"""

from __future__ import annotations

import logging
import math
import re
import threading
import time
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

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
from app.core.taxonomy import AgentId
from app.kb.data_model import DataEntry, load_data
from app.kb.index import embed_text, get_index
from app.kb.registry import load_sources
from app.kb.text import detect_query_language, match_terms

log = logging.getLogger(__name__)

NO_SOURCE = "No supporting source found in the knowledge base"
NO_SOURCE_AR = "لم يُعثر على مصدر داعم في قاعدة المعرفة"
OFFLINE_LABEL = "Answered from knowledge base data (no AI generation)."
PASSAGE_LABEL = "Passage from source document"
DISCLAIMER = {
    "en": "Informational only, not legal advice. The official Arabic text prevails.",
    "ar": "لأغراض المعلومات فقط وليست استشارة قانونية. يسود النص العربي الرسمي.",
    "az": "Yalnız məlumat xarakterlidir, hüquqi məsləhət deyil. Rəsmi ərəb mətni üstünlük təşkil edir.",
}
GUIDANCE = {
    "en": "Hello! I answer questions about UAE rules for the smart-pen screening service, using only the "
          "knowledge base (no AI generation). Try: \"What consent is required to process a child's personal data?\", "
          "\"Can an app show ads to minors?\" or \"Must a counsellor review a flag before parents are told?\"",
    "ar": "مرحباً! أجيب عن الأسئلة المتعلقة بالقواعد الإماراتية لخدمة القلم الذكي من قاعدة المعرفة فقط (دون توليد بالذكاء "
          "الاصطناعي). جرّب: «ما الموافقة المطلوبة لمعالجة البيانات الشخصية للطفل؟» أو «هل يجوز عرض إعلانات موجهة للقاصرين؟»",
    "az": "Salam! Ağıllı qələm xidməti üçün BƏƏ qaydaları ilə bağlı suallara yalnız bilik bazası əsasında cavab verirəm "
          "(süni intellekt generasiyası yoxdur). Məsələn: \"Uşağın şəxsi məlumatlarını emal etmək üçün hansı razılıq "
          "lazımdır?\" və ya \"Tətbiq azyaşlılara reklam göstərə bilərmi?\"",
}
EXAMPLES = {
    "en": ["What consent is required to process a child's personal data?", "Can an app show targeted ads to minors?",
           "Must a counsellor review a screening flag before parents or the student are told?"],
    "ar": ["ما الموافقة المطلوبة لمعالجة البيانات الشخصية للطفل؟", "هل يجوز لتطبيق عرض إعلانات موجهة للقاصرين؟",
           "هل يجب أن يراجع المرشد مؤشر الفحص قبل إبلاغ الوالدين؟"],
    "az": ["Uşağın şəxsi məlumatlarını emal etmək üçün hansı razılıq lazımdır?",
           "Tətbiq azyaşlılara hədəfli reklam göstərə bilərmi?",
           "Valideynlərə bildirməzdən əvvəl məsləhətçi siqnalı nəzərdən keçirməlidirmi?"],
}
GENERAL_UNAVAILABLE = {
    "en": "General AI answers need an LLM, and offline mode never calls one. Switch back to \"Grounded in knowledge "
          "base\", or set ANTHROPIC_API_KEY and LLM_PROVIDER=anthropic in .env.",
    "ar": "تتطلب الإجابات العامة نموذج ذكاء اصطناعي، والوضع غير المتصل لا يستدعي أي نموذج. عُد إلى «مستندة إلى قاعدة المعرفة».",
    "az": "Ümumi AI cavabları üçün LLM lazımdır, oflayn rejim isə heç vaxt LLM çağırmır. \"Bilik bazasına əsaslanan\" "
          "rejimə qayıdın.",
}
_GREETING = re.compile(
    r"\b(hi|hello|hey|hiya|yo|thanks|thank you|thx|good (morning|afternoon|evening|night)|how are you|who are you|"
    r"what can you do|help|ok|okay|bye|goodbye|salam|salamlar|salam aleykum|necəsən|necesen|sağ ol|sag ol|"
    r"təşəkkür(lər)?|təşəkkür edirəm|xahiş edirəm|sabahınız xeyir|günortanız xeyir|axşamınız xeyir)\b"
    r"|مرحبا|مرحباً|اهلا|أهلا|السلام عليكم|شكرا|شكراً|صباح الخير|مساء الخير|كيف حالك|من انت|من أنت",
    re.I,
)


# ------------------------------------------------------------------ scoring
def coverage(q_terms: list[str], doc_terms: set[str], idf: dict[str, float], default_idf: float) -> float:
    """IDF-weighted share of the query's distinct content terms found in the document.
    A word counts if the word or its light stem (~prefix) matches; unknown words keep full weight,
    so off-topic questions score low."""
    words = [t for t in dict.fromkeys(q_terms) if not t.startswith("~")]
    if not words:
        return 0.0
    stems = {t for t in q_terms if t.startswith("~")}
    got = total = 0.0
    for w in words:
        wt = idf.get(w, default_idf)
        total += wt
        stem = "~" + (w[:4] if re.search(r"[؀-ۿ]", w) else w[:5])
        if w in doc_terms or (stem in stems and stem in doc_terms):
            got += wt
    return got / total if total else 0.0


def _idf(docs: list[set[str]]) -> tuple[dict[str, float], float]:
    n = len(docs)
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) + 0.5 for t, c in df.items()}
    # words the corpus never uses weigh as much as an average word: a fully off-topic question still
    # scores 0, but one unusual word does not sink an otherwise strong match
    avg = sum(idf.values()) / len(idf) if idf else 1.0
    return idf, avg


def _dense_available() -> bool:
    s = get_settings()
    if s.offline_dense == "off":
        return False
    if s.embedding_provider == "hash":
        return True
    if s.offline_dense == "on":
        return True
    if s.embedding_provider != "sentence_transformers":
        return False
    try:  # auto: only if bge-m3 is already on disk; never trigger a 2 GB download from a question
        from huggingface_hub import try_to_load_from_cache

        return isinstance(try_to_load_from_cache(s.embedding_model, "config.json"), str)
    except Exception:
        return False


# ------------------------------------------------------------------ the JSON entry index
@dataclass
class _Entry:
    e: DataEntry
    terms: set[str]
    tokens: list[str]
    vec: list[float] | None = None


def _entry_text(e: DataEntry) -> str:
    kw = " ".join(e.keywords.en + e.keywords.ar + e.keywords.az)
    return f"{e.topic}\n{e.question}\n{kw}\n{e.answer}"


class DataIndex:
    def __init__(self):
        self._sig = None
        self._lock = threading.Lock()
        self.items: list[_Entry] = []
        self.errors: list[str] = []
        self.idf: dict[str, float] = {}
        self.default_idf = 1.0
        self.bm25 = None
        self.dense = False

    def _signature(self, d: Path):
        return tuple((p.name, p.stat().st_mtime_ns) for p in sorted(d.glob("*.json"))) if d.exists() else ()

    def ensure(self) -> DataIndex:
        d = get_settings().data_dir
        sig = (str(d), self._signature(d), _dense_available())
        if sig == self._sig:
            return self
        with self._lock:
            if sig == self._sig:
                return self
            from rank_bm25 import BM25Okapi

            r = load_data(d)
            self.errors = r.errors
            live = [e for e in r.entries if e.status != "retired"]
            self.items = [_Entry(e, set(match_terms(_entry_text(e))), match_terms(_entry_text(e))) for e in live]
            self.idf, self.default_idf = _idf([it.terms for it in self.items])
            self.bm25 = BM25Okapi([it.tokens for it in self.items]) if self.items else None
            self.dense = sig[2] and bool(self.items)
            if self.dense:
                try:
                    from app.kb.embeddings import get_embedder

                    vecs = get_embedder().embed([f"{it.e.question}\n{' '.join(it.e.keywords.en + it.e.keywords.ar + it.e.keywords.az)}"
                                                 for it in self.items])
                    for it, v in zip(self.items, vecs, strict=True):
                        it.vec = v
                except Exception as e:  # semantic matching is a bonus, never a requirement
                    log.warning("offline: embeddings unavailable (%s); using keyword matching only", e)
                    self.dense = False
            self._sig = sig
            log.info("offline: %d entries indexed (semantic=%s)", len(self.items), self.dense)
        return self


_data_index = DataIndex()


def get_data_index() -> DataIndex:
    return _data_index.ensure()


@dataclass
class Match:
    entry: DataEntry
    score: float
    lexical: float
    dense: float | None


def match_entries(question: str) -> list[Match]:
    idx = get_data_index()
    if not idx.items:
        return []
    q = match_terms(question)
    bm = idx.bm25.get_scores(q) if idx.bm25 is not None and q else [0.0] * len(idx.items)
    qv = None
    if idx.dense:
        from app.kb.embeddings import get_embedder

        qv = get_embedder().embed([question])[0]
    out = []
    for it, b in zip(idx.items, bm, strict=True):
        lex = coverage(q, it.terms, idx.idf, idx.default_idf)
        dn = None
        score = lex
        if qv is not None and it.vec is not None:
            dn = sum(a * c for a, c in zip(qv, it.vec, strict=True))
            dnorm = min(1.0, max(0.0, (dn - 0.35) / 0.4))  # bge-m3 cosine ~0.35 unrelated .. ~0.75 same meaning
            score = 0.6 * lex + 0.4 * dnorm
        out.append((score, float(b), Match(it.e, round(score, 4), round(lex, 4), None if dn is None else round(dn, 4))))
    out.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [m for *_, m in out]


# ------------------------------------------------------------------ extractive fallback
def match_passages(question: str) -> list[tuple[dict, float]]:
    idx = get_index()
    if not idx.chunks:
        return []
    q = match_terms(question)
    docs = [set(match_terms(embed_text(c))) for c in idx.chunks]
    idf, dflt = _idf(docs)
    scored = []
    for c, terms in zip(idx.chunks, docs, strict=True):
        if c.get("status") == "repealed":
            continue
        sc = coverage(q, terms, idf, dflt)
        if sc > 0:
            scored.append((c, round(sc, 4)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:10]


# ------------------------------------------------------------------ pipeline
def _resp(**kw) -> dict:
    return AskResponse(**kw).model_dump(mode="json")


async def run(req: AskRequest) -> AsyncIterator[tuple[str, dict]]:
    s = get_settings()
    t0 = time.perf_counter()
    q = req.question.strip()
    lang = req.language or detect_query_language(q)
    conv = req.conversation_id or f"conv_{uuid.uuid4().hex[:10]}"
    aid = f"ans_{uuid.uuid4().hex[:10]}"
    audit = get_audit()
    steps = [f"Offline mode (no LLM). Language detected: {lang}"]

    def log_audit(mode: str, outcome: str, *, entry: str | None = None, score: float | None = None,
                  refs: list[RetrievedChunkRef] | None = None, **kw):
        steps.append(f"Result: {mode}" + (f" (entry {entry}, score {score})" if entry else ""))
        return audit.log(kind="ask", mode=mode, outcome=outcome, matched_entry=entry, score=score,
                         agent=AgentId.LEGAL_ADVISER, input_event=q, retrieved_chunks=refs or [],
                         reasoning_steps=steps, recommendation=entry,
                         llm={"provider": "offline", "llm_calls": 0,
                              "latency_ms": int((time.perf_counter() - t0) * 1000)}, **kw)

    def guidance(text: str) -> dict:
        e = log_audit("guidance", "guidance")
        return _resp(answer_id=aid, conversation_id=conv, outcome="guidance", mode="guidance", language=lang,
                     answer=AnswerSections(short_answer=text, legal_basis=[], details=None, status_and_limits="",
                                           related=[], disclaimer=DISCLAIMER[lang]),
                     suggested_topics=EXAMPLES[lang], audit_id=e.audit_id)

    # 1. general mode cannot work offline; greetings / small talk get guidance
    if req.mode == "general":
        steps.append("General AI mode requested but offline mode never calls an LLM")
        yield "final", guidance(GENERAL_UNAVAILABLE[lang])
        return
    content = [t for t in match_terms(_GREETING.sub(" ", q)) if not t.startswith("~")]
    if not content:
        steps.append("Greeting or small talk: no content words to search for")
        yield "final", guidance(GUIDANCE[lang])
        return

    # 2. structured entries
    matches = match_entries(q)
    top = matches[0] if matches else None
    refs = [RetrievedChunkRef(chunk_id=f"data:{m.entry.id}", doc_id="kb/data", article=None, url="", score=m.score)
            for m in matches[:5]]
    steps.append(f"Matched {len(matches)} JSON entries; best {top.entry.id if top else '-'} score "
                 f"{top.score if top else 0} (lexical {top.lexical if top else 0}, semantic "
                 f"{top.dense if top and top.dense is not None else 'off'}); threshold {s.offline_min_score}")
    yield "retrieval", {"chunks": [r.model_dump() for r in refs], "best_score": top.score if top else 0.0,
                        "threshold": s.offline_min_score}

    if top and top.score >= s.offline_min_score:
        e = top.entry
        cits = [Citation(
            id=f"c{i}", chunk_id=f"data:{e.id}:{i}", doc_id=f"data:{e.id}", title=c.law, law_number=None, year=None,
            article=c.article, clause=None, quote=c.quote, url=c.url, layer=c.layer, status="unknown",
            language="en", score=top.score, verified=c.verified,
        ) for i, c in enumerate(e.citations, 1)]
        all_ver = bool(cits) and all(c.verified for c in cits)
        limits = [OFFLINE_LABEL, f"Entry '{e.id}' (status: {e.status}; last checked: {e.last_checked or 'never'})."]
        if not cits:
            limits.append("This entry has no citations.")
        elif not all_ver:
            limits.append("Sources marked 'Source to be verified' have not yet been checked against the official text.")
        related = [m.entry.question for m in matches[1:4] if m.score >= s.offline_min_score * 0.6]
        ent = log_audit("offline_json", "answered", entry=e.id, score=top.score, refs=refs,
                        citations=[c.chunk_id for c in cits], confidence=top.score,
                        pipeline_nodes=e.pipeline_nodes, readiness_dimensions=e.readiness_dimensions,
                        requires_human_decision=e.requires_human_decision)
        yield "final", _resp(
            answer_id=aid, conversation_id=conv, outcome="answered", mode="offline_json", language=lang,
            matched_entry=e.id,
            answer=AnswerSections(short_answer=e.answer, legal_basis=cits,
                                  details=f"Source of this answer: knowledge-base entry \u201c{e.question}\u201d "
                                          f"(topic: {e.topic}; id: {e.id}). The text is shown exactly as stored.",
                                  status_and_limits=" ".join(limits), related=related, disclaimer=DISCLAIMER[lang]),
            pipeline_nodes=e.pipeline_nodes, readiness_dimensions=e.readiness_dimensions,
            verification=VerificationReport(passed=all_ver, checked=len(cits), verified=sum(c.verified for c in cits),
                                            warnings=[] if all_ver else ["Source to be verified"]),
            requires_human_decision=e.requires_human_decision, audit_id=ent.audit_id,
        )
        return

    # 3. extractive fallback over ingested documents (verbatim passages, no generation)
    passages = match_passages(q)
    best_p = passages[0][1] if passages else 0.0
    steps.append(f"Extractive search over {len(get_index().chunks)} document chunks; best passage score {best_p} "
                 f"(threshold {s.extractive_min_score})")
    if passages and best_p >= s.extractive_min_score:
        keep = [(c, sc) for c, sc in passages[:3] if sc >= max(s.extractive_min_score, best_p * 0.8)]
        docs = {d.doc_id: d for d in load_sources(s.kb_dir)}
        cits = []
        for i, (c, sc) in enumerate(keep, 1):
            d = docs.get(c["doc_id"])
            cits.append(Citation(
                id=f"p{i}", chunk_id=c["chunk_id"], doc_id=c["doc_id"], title=c.get("title") or c["doc_id"],
                law_number=c.get("law_number") or None, year=int(c["year"]) if c.get("year") else None,
                article=c.get("article"), clause=None, quote=c["text"], url=c.get("url") or "",
                layer=c.get("layer") or "uae_federal", status=c.get("status") or "unknown",
                language=c.get("language") or "en", score=sc, verified=bool(d and d.verified),
            ))
        prefs = [RetrievedChunkRef(chunk_id=c["chunk_id"], doc_id=c["doc_id"], article=c.get("article"),
                                   url=c.get("url") or "", score=sc) for c, sc in passages[:5]]
        ent = log_audit("extractive", "answered", score=best_p, refs=prefs, citations=[c.chunk_id for c in cits],
                        confidence=best_p)
        all_ver = all(c.verified for c in cits)
        yield "final", _resp(
            answer_id=aid, conversation_id=conv, outcome="answered", mode="extractive", language=lang,
            answer=AnswerSections(
                short_answer=f"{PASSAGE_LABEL}: {len(cits)} matching passage(s), shown verbatim below. No summary or "
                             "AI generation; read the passages and check the official text.",
                legal_basis=cits, details=None,
                status_and_limits=OFFLINE_LABEL + ("" if all_ver else
                                                   " The source document is registered but not yet human-verified."),
                related=[], disclaimer=DISCLAIMER[lang]),
            verification=VerificationReport(passed=all_ver, checked=len(cits), verified=sum(c.verified for c in cits)),
            audit_id=ent.audit_id,
        )
        return

    # 4. no source
    topics = [m.entry.topic for m in matches[:3] if m.score > 0] or sorted({it.e.topic for it in get_data_index().items})[:4]
    ent = log_audit("no_source", "no_source", score=top.score if top else 0.0, refs=refs)
    yield "final", _resp(
        answer_id=aid, conversation_id=conv, outcome="no_source", mode="no_source", language=lang,
        no_source_message=NO_SOURCE_AR if lang == "ar" else NO_SOURCE,
        suggested_topics=list(dict.fromkeys(topics)), audit_id=ent.audit_id,
    )
