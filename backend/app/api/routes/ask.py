import json
import logging

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.agents import router as pipeline
from app.api.schemas import AskRequest, AskResponse, ErrorResponse
from app.core.config import get_settings
from app.kb.index import get_index
from app.llm import get_llm

log = logging.getLogger(__name__)
router = APIRouter(tags=["legal search"])


def _llm_error(e: Exception) -> dict:
    name = type(e).__name__
    msg = str(e)
    if name == "AuthenticationError":
        msg = "The LLM provider rejected the API key. Check ANTHROPIC_API_KEY in .env."
    elif name == "NotFoundError":
        msg = "The LLM model was not found. Check LLM_MODEL / LLM_ROUTER_MODEL in .env."
    elif name in {"APIConnectionError", "ConnectError", "ConnectTimeout"}:
        msg = "Cannot reach the LLM provider (network)."
    elif name == "RateLimitError":
        msg = "The LLM provider is rate-limiting requests. Try again shortly."
    return {"code": "llm_unavailable", "message": msg, "details": {"type": name}}


def _preflight(req: AskRequest) -> None:
    if get_settings().offline:
        return  # offline mode needs no LLM and always answers (entry, passage, guidance or no_source)
    try:
        get_llm()
    except Exception as e:
        raise HTTPException(503, detail={"code": "llm_unavailable", "message": str(e)}) from e
    if req.mode == "grounded" and not get_index().chunks:
        raise HTTPException(409, detail={
            "code": "kb_empty",
            "message": "The knowledge base is empty. Put documents in kb/raw and run: python -m app.kb.ingest"})


@router.post(
    "/ask",
    response_model=AskResponse,
    responses={409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Ask a legal question (JSON, or SSE when stream=true)",
)
async def ask(req: AskRequest, stream: bool = Query(False)):
    _preflight(req)

    if not stream:
        final = None
        try:
            async for ev, data in pipeline.run(req):
                if ev == "final":
                    final = data
        except Exception as e:
            log.exception("ask failed")
            raise HTTPException(503, detail=_llm_error(e)) from e
        return final

    async def events():
        try:
            async for ev, data in pipeline.run(req):
                yield {"event": ev, "data": json.dumps(data, ensure_ascii=False)}
        except Exception as e:
            log.exception("ask stream failed")
            yield {"event": "error", "data": json.dumps(_llm_error(e), ensure_ascii=False)}

    return EventSourceResponse(events(), ping=15)
