"""API contract (Pydantic v2). Mirrors docs/api.md and frontend/src/lib/types.ts.

Change this file first, then the doc, then the TS types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.taxonomy import (
    AgentId,
    Domain,
    GapType,
    KBLayer,
    LegalStatus,
    PipelineNode,
    ReadinessDimension,
)

Lang = Literal["en", "ar", "az"]


# ---------------------------------------------------------------- errors
class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------------------------------------------------------------- health / meta
class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    llm_provider: str
    llm_model: str
    llm_configured: bool = Field(..., description="False when ANTHROPIC_API_KEY is missing")
    embedding_provider: str
    embedding_model: str
    kb_documents: int
    kb_chunks: int
    index_chunks: int = Field(..., description="Vectors in Chroma; 0 means run ingest")
    answer_mode: str = Field("llm", description="offline (JSON data + verbatim passages, no LLM) | llm")
    data_entries: int = 0
    data_errors: list[str] = Field(default_factory=list)
    semantic_search: bool = Field(False, description="bge-m3 used for offline matching")
    audit_entries: int
    problems: list[str] = Field(default_factory=list)


class TaxonomyItem(BaseModel):
    id: str
    label: str


class TaxonomyResponse(BaseModel):
    pipeline_nodes: list[TaxonomyItem]
    readiness_dimensions: list[TaxonomyItem]
    layers: list[str]
    gap_types: list[str]
    domains: list[str]
    agents: list[str]


# ---------------------------------------------------------------- KB / sources
class SourceDocument(BaseModel):
    doc_id: str = Field(..., examples=["uae-fdl-xx-yyyy-pdp-ar"])
    title: str
    title_ar: str | None = None
    issuing_body: str
    law_number: str | None = None
    year: int | None = None
    status: LegalStatus
    layer: KBLayer
    language: Lang
    translation_of: str | None = Field(None, description="doc_id of the authoritative Arabic original")
    amends: list[str] = Field(default_factory=list, description="doc_ids this document amends")
    amended_by: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    url: str
    retrieved_at: str | None = None  # ISO date the file was downloaded
    verified: bool = Field(False, description="Human-verified against the official source")
    chunk_count: int = 0


class CoverageCell(BaseModel):
    layer: KBLayer
    domain: Domain
    documents: int


class SourcesResponse(BaseModel):
    documents: list[SourceDocument]
    coverage: list[CoverageCell]
    total_documents: int
    total_chunks: int


class Article(BaseModel):
    article: str = Field(..., examples=["7"])
    heading: str | None = None
    chapter: str | None = None
    text: str
    chunk_ids: list[str]
    amended: bool = False


class LawDetail(BaseModel):
    document: SourceDocument
    articles: list[Article]
    translations: list[str] = Field(default_factory=list, description="doc_ids of linked translations")


# ---------------------------------------------------------------- ask / answers
class AskFilters(BaseModel):
    layers: list[KBLayer] = Field(default_factory=lambda: [KBLayer.UAE_FEDERAL, KBLayer.EMIRATE])
    include_repealed: bool = False
    domains: list[Domain] = Field(default_factory=list)


AskMode = Literal["grounded", "general"]
# What actually produced the answer (response only)
AnswerMode = Literal["grounded", "general", "offline_json", "extractive", "no_source", "guidance"]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    mode: AskMode = Field("grounded", description="general = plain AI answer, not from the KB, no citations")
    language: Lang | None = Field(None, description="Auto-detected when omitted")
    conversation_id: str | None = None
    agent: AgentId = AgentId.LEGAL_ADVISER
    filters: AskFilters = Field(default_factory=AskFilters)


class Citation(BaseModel):
    id: str = Field(..., description="Citation marker used inline, e.g. 'c1'")
    chunk_id: str
    doc_id: str
    title: str
    law_number: str | None = None
    year: int | None = None
    article: str | None = None
    clause: str | None = None
    quote: str = Field(..., description="Exact substring of the chunk text")
    url: str
    layer: KBLayer
    status: LegalStatus
    language: Lang
    score: float
    verified: bool = Field(..., description="Set by the citation checker, never by the LLM")


class VerificationReport(BaseModel):
    passed: bool = Field(..., description="True only if every remaining citation was verified and at least one exists")
    checked: int
    verified: int
    removed: list[str] = Field(default_factory=list, description="Claims/citations removed as unverifiable")
    warnings: list[str] = Field(default_factory=list)


class AnswerSections(BaseModel):
    """The six-part answer format. Text fields use inline markers like [c1]."""

    short_answer: str
    legal_basis: list[Citation]
    details: str | None = None
    status_and_limits: str
    related: list[str] = Field(default_factory=list)
    disclaimer: str


class AskResponse(BaseModel):
    answer_id: str
    conversation_id: str
    outcome: Literal["answered", "no_source", "general", "guidance"]
    mode: AnswerMode = "grounded"
    matched_entry: str | None = Field(None, description="offline_json: id of the kb/data entry that answered")
    language: Lang
    answer: AnswerSections | None = None  # null when outcome == no_source
    no_source_message: str | None = None
    suggested_topics: list[str] = Field(default_factory=list)
    pipeline_nodes: list[PipelineNode] = Field(default_factory=list)
    readiness_dimensions: list[ReadinessDimension] = Field(default_factory=list)
    verification: VerificationReport | None = None
    requires_human_decision: bool = False
    audit_id: str


# ---------------------------------------------------------------- agents / scenarios
AgentState = Literal["idle", "thinking", "done", "error"]


class AgentAssessment(BaseModel):
    agent: AgentId
    summary: str
    recommendation: str
    confidence: float = Field(..., ge=0, le=1)
    citations: list[Citation]
    pipeline_nodes: list[PipelineNode]
    readiness_dimensions: list[ReadinessDimension]
    requires_human_decision: bool
    audit_id: str


class Conflict(BaseModel):
    agents: list[AgentId]
    topic: str
    description: str


class CoordinatorRecommendation(BaseModel):
    recommendation: str
    actions: list[str]
    conflicts: list[Conflict]
    requires_human_decision: bool
    review_id: str | None = None
    citations: list[Citation]
    audit_id: str


class ScenarioEventDef(BaseModel):
    id: str
    step: int
    at: str = Field(..., description="Simulated time, e.g. 'T+6 months'")
    title: str
    description: str
    severity: Literal["info", "warning", "critical"]
    visible_to: list[AgentId]
    pipeline_nodes: list[PipelineNode]


class ScenarioSummary(BaseModel):
    id: str
    title: str
    description: str
    controversial: bool = False
    total_events: int


class StartScenarioResponse(BaseModel):
    run_id: str
    scenario: ScenarioSummary
    stream_url: str


class NextEventRequest(BaseModel):
    run_id: str


class NextEventResponse(BaseModel):
    run_id: str
    released: ScenarioEventDef | None
    remaining: int


class StreamEnvelope(BaseModel):
    """Every SSE `data:` payload. `type` mirrors the SSE `event:` name."""

    type: Literal[
        "run_started",
        "event_released",
        "agent_status",
        "agent_step",
        "agent_assessment",
        "conflict_detected",
        "coordinator_recommendation",
        "human_review_required",
        "pipeline_highlight",
        "run_completed",
        "review_recorded",
        "error",
    ]
    run_id: str
    seq: int
    ts: datetime
    data: dict[str, Any]


# ---------------------------------------------------------------- human review
class ReviewDecisionRequest(BaseModel):
    decision: Literal["approve", "override", "escalate"]
    reviewer_role: Literal["counsellor", "regulator", "school_admin"]
    comment: str = Field(..., min_length=3, max_length=2000)


class ReviewDecisionResponse(BaseModel):
    review_id: str
    decision: str
    audit_id: str


# ---------------------------------------------------------------- gaps
class GapCitation(BaseModel):
    law: str
    article: str
    layer: KBLayer
    url: str = ""
    quote: str
    verified: bool = False


class GapSide(BaseModel):
    statement: str
    citations: list[GapCitation] = Field(default_factory=list)


class PolicyGap(BaseModel):
    id: str
    title: str
    gap_type: GapType
    domain: Domain
    uae_says: GapSide
    global_example_says: GapSide
    gap_analysis: str = Field(..., description="Explicitly analysis, not law")
    recommendation: str
    severity: Literal["low", "medium", "high"]
    pipeline_nodes: list[PipelineNode]
    readiness_dimensions: list[ReadinessDimension]
    audit_id: str | None = None


class GapsResponse(BaseModel):
    gaps: list[PolicyGap]
    readiness_radar: dict[ReadinessDimension, float] = Field(
        default_factory=dict, description="0-1 gap pressure per dimension, for the radar chart"
    )


# ---------------------------------------------------------------- audit
class RetrievedChunkRef(BaseModel):
    chunk_id: str
    doc_id: str
    article: str | None = None
    url: str
    score: float


class AuditEntry(BaseModel):
    audit_id: str
    timestamp: datetime
    kind: Literal["ask", "agent", "coordinator", "gap", "scenario_event", "human_decision", "system"]
    mode: str | None = Field(None, description="grounded | general | offline_json | extractive | no_source | guidance")
    outcome: str | None = None
    matched_entry: str | None = None
    score: float | None = None
    agent: AgentId | None = None
    run_id: str | None = None
    input_event: str
    retrieved_chunks: list[RetrievedChunkRef] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    citations: list[str] = Field(default_factory=list, description="chunk_ids actually cited")
    confidence: float | None = None
    pipeline_nodes: list[PipelineNode] = Field(default_factory=list)
    readiness_dimensions: list[ReadinessDimension] = Field(default_factory=list)
    requires_human_decision: bool = False
    llm: dict[str, Any] | None = Field(None, description="provider, model, token usage, latency_ms")


class AuditResponse(BaseModel):
    entries: list[AuditEntry]
    total: int


# ---------------------------------------------------------------- kb/data entries (offline mode)
class DataEntrySummary(BaseModel):
    id: str
    topic: str
    question: str
    status: str
    last_checked: str | None
    layers: list[KBLayer]
    citations: int
    verified_citations: int
    file: str


class DataEntriesResponse(BaseModel):
    entries: list[DataEntrySummary]
    errors: list[str]
