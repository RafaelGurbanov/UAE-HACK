from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.api.deps import get_audit
from app.api.schemas import AuditResponse
from app.core.taxonomy import AgentId, PipelineNode

router = APIRouter()


@router.get("/audit", response_model=AuditResponse, tags=["audit"])
def list_audit(
    agent: AgentId | None = None,
    run_id: str | None = None,
    kind: str | None = None,
    since: datetime | None = None,
    node: PipelineNode | None = None,
    requires_human: bool | None = None,
    outcome: str | None = Query(None, description="Result: answered, no_source, guidance, assessed, conflict, approve, ..."),
    limit: int = Query(200, ge=1, le=5000),
) -> AuditResponse:
    entries = get_audit().read(agent=agent.value if agent else None, run_id=run_id, kind=kind, since=since,
                               node=node.value if node else None, requires_human=requires_human, outcome=outcome)
    return AuditResponse(entries=entries[:limit], total=len(entries))


@router.get("/audit/export", tags=["audit"], summary="Download the audit log (jsonl or json)")
def export_audit(format: str = Query("jsonl", pattern="^(jsonl|json)$"), run_id: str | None = None) -> Response:
    entries = get_audit().read(run_id=run_id)
    if format == "json":
        body = "[" + ",".join(e.model_dump_json() for e in entries) + "]"
        media = "application/json"
    else:
        body = "\n".join(e.model_dump_json() for e in entries) + ("\n" if entries else "")
        media = "application/x-ndjson"
    return Response(body, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="audit.{format}"'})
