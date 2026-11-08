from fastapi import APIRouter

from app.api.deps import get_audit
from app.api.schemas import HealthResponse, TaxonomyItem, TaxonomyResponse
from app.core.config import get_settings
from app.core.taxonomy import PIPELINE_NODE_LABELS, READINESS_LABELS, AgentId, Domain, GapType, KBLayer
from app.kb.index import get_index
from app.kb.registry import load_sources

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = get_settings()
    docs = load_sources(s.kb_dir)
    problems: list[str] = []
    try:
        idx = get_index()
        index_chunks = idx.dense_count()
        kb_chunks = len(idx.chunks)
    except Exception as e:  # never let health crash
        problems.append(f"Index could not be loaded: {e}")
        index_chunks = kb_chunks = 0
    data_errors: list[str] = []
    data_entries = 0
    semantic = False
    if s.offline:
        from app.agents.offline import get_data_index

        di = get_data_index()
        data_errors, data_entries, semantic = di.errors, len(di.items), di.dense
        if data_errors:
            problems.append(f"{len(data_errors)} problem(s) in kb/data: run python -m app.kb.validate_data")
        if data_entries == 0 and kb_chunks == 0:
            problems.append("No kb/data entries and no ingested documents: offline mode can only refuse")
    else:
        if not s.llm_configured:
            problems.append("ANTHROPIC_API_KEY is not set in .env")
        if kb_chunks == 0:
            problems.append("Knowledge base is empty: put documents in kb/raw and run python -m app.kb.ingest")
        elif index_chunks == 0:
            problems.append("No vectors in the index: run python -m app.kb.ingest")
    if s.embedding_provider == "hash":
        problems.append("EMBEDDING_PROVIDER=hash is a test-only embedder")
    return HealthResponse(
        status="ok" if not problems else "degraded", version=s.app_version,
        llm_provider=s.effective_provider, llm_model="none (offline)" if s.offline else s.llm_model,
        llm_configured=s.llm_configured, answer_mode="offline" if s.offline else "llm",
        data_entries=data_entries, data_errors=data_errors, semantic_search=semantic,
        embedding_provider=s.embedding_provider, embedding_model=s.embedding_model,
        kb_documents=len(docs), kb_chunks=kb_chunks, index_chunks=index_chunks,
        audit_entries=get_audit().count(), problems=problems,
    )


@router.get("/meta/taxonomy", response_model=TaxonomyResponse)
def taxonomy() -> TaxonomyResponse:
    return TaxonomyResponse(
        pipeline_nodes=[TaxonomyItem(id=k.value, label=v) for k, v in PIPELINE_NODE_LABELS.items()],
        readiness_dimensions=[TaxonomyItem(id=k.value, label=v) for k, v in READINESS_LABELS.items()],
        layers=[x.value for x in KBLayer], gap_types=[x.value for x in GapType],
        domains=[x.value for x in Domain], agents=[x.value for x in AgentId],
    )
