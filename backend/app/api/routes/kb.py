from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import Article, LawDetail, SourcesResponse
from app.core.config import get_settings
from app.core.taxonomy import KBLayer, LegalStatus
from app.kb.index import get_index
from app.kb.registry import coverage, load_sources

router = APIRouter(tags=["knowledge base"])


@router.get("/sources", response_model=SourcesResponse)
def list_sources(
    layer: KBLayer | None = None,
    status: LegalStatus | None = None,
    language: str | None = Query(None, pattern="^(en|ar)$"),
) -> SourcesResponse:
    docs = load_sources(get_settings().kb_dir)
    if layer:
        docs = [d for d in docs if d.layer == layer]
    if status:
        docs = [d for d in docs if d.status == status]
    if language:
        docs = [d for d in docs if d.language == language]
    return SourcesResponse(documents=docs, coverage=coverage(docs), total_documents=len(docs),
                           total_chunks=sum(d.chunk_count for d in docs))


@router.get("/laws/{doc_id}", response_model=LawDetail)
def get_law(doc_id: str) -> LawDetail:
    docs = {d.doc_id: d for d in load_sources(get_settings().kb_dir)}
    if doc_id not in docs:
        raise HTTPException(404, detail={"code": "not_found", "message": f"Unknown doc_id '{doc_id}'"})
    chunks = [c for c in get_index().chunks if c["doc_id"] == doc_id]
    articles: list[Article] = []
    for c in chunks:  # chunks are stored in document order; merge parts of the same article
        key = c.get("article") or c.get("heading") or c["chunk_id"]
        if articles and articles[-1].article == key and c.get("part"):
            articles[-1].text += "\n\n" + c["text"]
            articles[-1].chunk_ids.append(c["chunk_id"])
            continue
        articles.append(Article(article=str(key), heading=c.get("heading"), chapter=c.get("chapter"),
                                text=c["text"], chunk_ids=[c["chunk_id"]]))
    d = docs[doc_id]
    translations = [x.doc_id for x in docs.values() if x.translation_of == doc_id]
    if d.translation_of:
        translations.append(d.translation_of)
    return LawDetail(document=d, articles=articles, translations=translations)
