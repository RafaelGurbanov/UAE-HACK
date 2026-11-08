import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    NextEventRequest,
    NextEventResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ScenarioEventDef,
    ScenarioSummary,
    StartScenarioResponse,
)
from app.scenarios.engine import ScenarioError, engine

router = APIRouter(tags=["scenarios"])


def _err(e: ScenarioError) -> HTTPException:
    return HTTPException(e.status, detail={"code": e.code, "message": e.message})


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios() -> list[ScenarioSummary]:
    return [ScenarioSummary(**engine.summary(s)) for s in engine.scenarios().values()]


@router.post("/scenarios/{scenario_id}/start", response_model=StartScenarioResponse)
def start(scenario_id: str) -> StartScenarioResponse:
    try:
        run = engine.start(scenario_id)
    except ScenarioError as e:
        raise _err(e) from e
    return StartScenarioResponse(run_id=run.run_id, scenario=ScenarioSummary(**engine.summary(run.scenario)),
                                 stream_url=f"/api/scenarios/{scenario_id}/stream?run_id={run.run_id}")


@router.get("/scenarios/{scenario_id}/stream", summary="SSE stream of run events (replays history; supports Last-Event-ID)")
async def stream(scenario_id: str, run_id: str, request: Request):
    try:
        run = engine.get_run(scenario_id, run_id)
    except ScenarioError as e:
        raise _err(e) from e
    last = int(request.headers.get("last-event-id") or 0)
    q: asyncio.Queue = asyncio.Queue()
    backlog = [e for e in run.log if e["seq"] > last]
    run.subscribers.append(q)

    async def gen():
        try:
            for env in backlog:
                yield {"id": str(env["seq"]), "data": json.dumps(env, ensure_ascii=False)}
            seen = backlog[-1]["seq"] if backlog else last
            while True:
                if await request.is_disconnected():
                    break
                try:
                    env = await asyncio.wait_for(q.get(), timeout=10)
                except TimeoutError:
                    continue
                if env["seq"] <= seen:
                    continue
                seen = env["seq"]
                yield {"id": str(env["seq"]), "data": json.dumps(env, ensure_ascii=False)}
        finally:
            if q in run.subscribers:
                run.subscribers.remove(q)

    return EventSourceResponse(gen(), ping=15)


@router.post("/scenarios/{scenario_id}/next", response_model=NextEventResponse)
async def next_event(scenario_id: str, req: NextEventRequest) -> NextEventResponse:
    try:
        ev, remaining = await engine.next_event(scenario_id, req.run_id)
    except ScenarioError as e:
        raise _err(e) from e
    return NextEventResponse(run_id=req.run_id, released=ScenarioEventDef(**ev) if ev else None, remaining=remaining)


@router.get("/scenarios/{scenario_id}/runs/{run_id}", summary="Full event history of a run (for reloads and tests)")
def run_history(scenario_id: str, run_id: str) -> dict:
    try:
        run = engine.get_run(scenario_id, run_id)
    except ScenarioError as e:
        raise _err(e) from e
    return {"run_id": run.run_id, "released": run.released, "finished": run.finished, "busy": run.busy,
            "events": run.log}


@router.post("/reviews/{review_id}/decision", response_model=ReviewDecisionResponse)
def review_decision(review_id: str, req: ReviewDecisionRequest) -> ReviewDecisionResponse:
    try:
        _, audit_id = engine.decide(review_id, req.decision, req.reviewer_role, req.comment)
    except ScenarioError as e:
        raise _err(e) from e
    return ReviewDecisionResponse(review_id=review_id, decision=req.decision, audit_id=audit_id)
