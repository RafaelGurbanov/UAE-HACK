"""Offline scenario engine: progressive events, information asymmetry, local rules.

No LLM is called. For each released event:
1. every agent in `visible_to` searches kb/data (the same matcher as offline search) with its rule's
   query, and produces an assessment from the YAML rule plus the entry it found. If nothing matches,
   it says "No supporting source found in the knowledge base" and its confidence is lowered;
2. the Coordinator compares stances; incompatible pairs are reported as conflicts;
3. if the coordinator rule requires a human decision, a review is opened.
Everything is streamed (SSE envelopes with increasing `seq`) and written to the audit log.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from app.api.deps import get_audit
from app.api.schemas import RetrievedChunkRef
from app.core.config import get_settings
from app.core.taxonomy import AgentId

log = logging.getLogger(__name__)

NO_SOURCE = "No supporting source found in the knowledge base"
AGENTS = ["data_protection", "education", "consumer_protection", "ai_ethics"]
# stance pairs that contradict each other (order-free)
INCOMPATIBLE = {frozenset(p) for p in [("suspend", "restrict"), ("suspend", "monitor"), ("allow", "prohibit"),
                                       ("proceed", "pause"), ("monitor", "prohibit"), ("restrict", "allow")]}


class ScenarioError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def load_scenarios(d: Path) -> dict[str, dict]:
    out = {}
    for f in sorted(d.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        data.setdefault("id", f.stem)
        data["events"] = sorted(data.get("events", []), key=lambda e: e.get("step", 0))
        out[data["id"]] = data
    return out


@dataclass
class Run:
    run_id: str
    scenario: dict
    released: int = 0
    seq: int = 0
    log: list[dict] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    busy: bool = False
    finished: bool = False


@dataclass
class Review:
    review_id: str
    run_id: str
    event_id: str
    summary: str
    decision: dict | None = None


class Engine:
    def __init__(self):
        self.runs: dict[str, Run] = {}
        self.reviews: dict[str, Review] = {}

    # ---------------------------------------------------------- helpers
    def scenarios(self) -> dict[str, dict]:
        return load_scenarios(get_settings().scenarios_dir)

    def get_run(self, scenario_id: str, run_id: str) -> Run:
        run = self.runs.get(run_id)
        if not run or run.scenario["id"] != scenario_id:
            raise ScenarioError(404, "not_found", f"Unknown run '{run_id}' for scenario '{scenario_id}'")
        return run

    def emit(self, run: Run, type_: str, data: dict) -> dict:
        run.seq += 1
        env = {"type": type_, "run_id": run.run_id, "seq": run.seq,
               "ts": datetime.now(UTC).isoformat(), "data": data}
        run.log.append(env)
        for q in list(run.subscribers):
            q.put_nowait(env)
        return env

    @staticmethod
    def summary(s: dict) -> dict:
        return {"id": s["id"], "title": s.get("title", s["id"]), "description": s.get("description", ""),
                "controversial": bool(s.get("controversial")), "total_events": len(s.get("events", []))}

    @staticmethod
    def public_event(ev: dict) -> dict:
        keys = ["id", "step", "at", "title", "description", "severity", "visible_to", "pipeline_nodes"]
        out = {k: ev.get(k) for k in keys}
        out["visible_to"] = [a for a in ev.get("visible_to", []) if a in AGENTS]
        return out

    # ---------------------------------------------------------- lifecycle
    def start(self, scenario_id: str) -> Run:
        sc = self.scenarios().get(scenario_id)
        if not sc:
            raise ScenarioError(404, "not_found", f"Unknown scenario '{scenario_id}'")
        run = Run(run_id=f"run_{uuid.uuid4().hex[:10]}", scenario=sc)
        self.runs[run.run_id] = run
        self.emit(run, "run_started", {"scenario": self.summary(sc), "agents": AGENTS})
        get_audit().log(kind="scenario_event", run_id=run.run_id, input_event=f"start:{scenario_id}",
                        mode="offline_rules", outcome="started", reasoning_steps=[f"Run started: {sc.get('title')}"],
                        llm={"provider": "offline", "llm_calls": 0})
        return run

    async def next_event(self, scenario_id: str, run_id: str) -> tuple[dict | None, int]:
        run = self.get_run(scenario_id, run_id)
        events = run.scenario["events"]
        if run.busy:
            raise ScenarioError(409, "busy", "The previous event is still being processed")
        if run.released >= len(events):
            raise ScenarioError(409, "finished", "All events have been released; restart the scenario")
        ev = events[run.released]
        run.released += 1
        run.busy = True
        pub = self.public_event(ev)
        self.emit(run, "event_released", pub)
        self.emit(run, "pipeline_highlight", {"nodes": ev.get("pipeline_nodes", []), "severity": ev.get("severity")})
        get_audit().log(kind="scenario_event", run_id=run.run_id, input_event=ev["id"], mode="offline_rules",
                        outcome=ev.get("severity"), pipeline_nodes=ev.get("pipeline_nodes", []),
                        reasoning_steps=[f"Event released: {ev.get('title')}",
                                         f"Visible to: {', '.join(pub['visible_to'])}"],
                        llm={"provider": "offline", "llm_calls": 0})
        delay = get_settings().scenario_step_delay
        if delay > 0:
            asyncio.get_running_loop().create_task(self._process(run, ev, delay))
        else:
            await self._process(run, ev, 0)
        return pub, len(events) - run.released

    async def _process(self, run: Run, ev: dict, delay: float) -> None:
        from app.agents.offline import match_entries

        s = get_settings()
        audit = get_audit()
        try:
            stances: dict[str, str] = {}
            rules = ev.get("assessments", {})
            for agent in [a for a in ev.get("visible_to", []) if a in AGENTS]:
                rule = rules.get(agent, {})
                self.emit(run, "agent_status", {"agent": agent, "state": "thinking", "event_id": ev["id"]})
                if delay:
                    await asyncio.sleep(delay)
                q = rule.get("query") or ev.get("description", "")
                self.emit(run, "agent_step", {"agent": agent, "event_id": ev["id"],
                                              "step": f"Searching the knowledge base: “{q}”"})
                matches = match_entries(q)
                top = matches[0] if matches and matches[0].score >= s.offline_min_score else None
                conf = float(rule.get("confidence", 0.6))
                stance = rule.get("stance", "monitor")
                if top:
                    e = top.entry
                    cites = [{"id": f"c{i}", "law": c.law, "article": c.article, "layer": c.layer.value,
                              "url": c.url, "quote": c.quote, "verified": c.verified}
                             for i, c in enumerate(e.citations, 1)]
                    summary = f"Matched knowledge-base entry “{e.question}” (score {top.score:.2f})."
                    nodes = [n.value for n in e.pipeline_nodes] or ev.get("pipeline_nodes", [])
                    dims = [d.value for d in e.readiness_dimensions]
                    requires_human = e.requires_human_decision
                else:
                    cites, nodes, dims, requires_human = [], ev.get("pipeline_nodes", []), [], True
                    summary = f"{NO_SOURCE}. Recommendation is based on the scenario rule only."
                    conf = round(conf * 0.5, 2)
                stances[agent] = stance
                refs = [RetrievedChunkRef(chunk_id=f"data:{m.entry.id}", doc_id="kb/data", url="", score=m.score)
                        for m in matches[:3]]
                entry = audit.log(
                    kind="agent", agent=AgentId(agent), run_id=run.run_id, input_event=ev["id"], mode="offline_rules",
                    outcome="assessed" if top else "no_source", matched_entry=top.entry.id if top else None,
                    score=top.score if top else (matches[0].score if matches else 0.0), retrieved_chunks=refs,
                    reasoning_steps=[f"Saw event: {ev.get('title')}", f"Searched: {q}", summary,
                                     f"Stance: {stance}"],
                    recommendation=rule.get("recommendation"), confidence=conf, pipeline_nodes=nodes,
                    readiness_dimensions=dims, requires_human_decision=requires_human,
                    llm={"provider": "offline", "llm_calls": 0},
                )
                self.emit(run, "agent_assessment", {
                    "agent": agent, "event_id": ev["id"], "summary": summary,
                    "recommendation": rule.get("recommendation", "No rule defined for this agent."),
                    "stance": stance, "confidence": conf, "no_source": top is None,
                    "matched_entry": top.entry.id if top else None, "citations": cites,
                    "pipeline_nodes": nodes, "readiness_dimensions": dims,
                    "requires_human_decision": requires_human, "audit_id": entry.audit_id,
                })
                self.emit(run, "agent_status", {"agent": agent, "state": "done", "event_id": ev["id"]})

            # coordinator
            self.emit(run, "agent_status", {"agent": "coordinator", "state": "thinking", "event_id": ev["id"]})
            if delay:
                await asyncio.sleep(delay)
            conflicts = []
            names = list(stances)
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    if frozenset((stances[a], stances[b])) in INCOMPATIBLE:
                        c = {"agents": [a, b], "topic": ev.get("title"),
                             "description": f"{a} recommends '{stances[a]}' but {b} recommends '{stances[b]}'."}
                        conflicts.append(c)
                        self.emit(run, "conflict_detected", c)
            crule = ev.get("coordinator", {})
            needs_human = bool(crule.get("requires_human_decision")) or bool(conflicts)
            review_id = None
            if needs_human:
                review_id = f"rev_{uuid.uuid4().hex[:10]}"
                self.reviews[review_id] = Review(review_id, run.run_id, ev["id"], crule.get("recommendation", ""))
            centry = audit.log(
                kind="coordinator", agent=AgentId.COORDINATOR, run_id=run.run_id, input_event=ev["id"],
                mode="offline_rules", outcome="conflict" if conflicts else "consensus",
                reasoning_steps=[f"Assessments from: {', '.join(names) or 'none'}",
                                 f"Conflicts: {len(conflicts)}", *[c["description"] for c in conflicts]],
                recommendation=crule.get("recommendation"), pipeline_nodes=ev.get("pipeline_nodes", []),
                requires_human_decision=needs_human, llm={"provider": "offline", "llm_calls": 0},
            )
            self.emit(run, "coordinator_recommendation", {
                "event_id": ev["id"], "recommendation": crule.get("recommendation", ""),
                "actions": crule.get("actions", []), "conflicts": conflicts,
                "expected_handling": ev.get("expected_handling", []), "requires_human_decision": needs_human,
                "review_id": review_id, "audit_id": centry.audit_id,
            })
            self.emit(run, "agent_status", {"agent": "coordinator", "state": "done", "event_id": ev["id"]})
            if review_id:
                self.emit(run, "human_review_required", {
                    "review_id": review_id, "event_id": ev["id"], "summary": crule.get("recommendation", ""),
                    "options": ["approve", "override", "escalate"]})
            if run.released >= len(run.scenario["events"]):
                run.finished = True
                self.emit(run, "run_completed", {"summary": f"All {run.released} events released."})
        except Exception as e:  # never leave the run stuck
            log.exception("scenario processing failed")
            self.emit(run, "error", {"code": "internal", "message": str(e)})
        finally:
            run.busy = False

    def decide(self, review_id: str, decision: str, role: str, comment: str) -> tuple[Review, str]:
        rev = self.reviews.get(review_id)
        if not rev:
            raise ScenarioError(404, "not_found", f"Unknown review '{review_id}'")
        if rev.decision:
            raise ScenarioError(409, "already_decided", f"Review already decided: {rev.decision['decision']}")
        entry = get_audit().log(
            kind="human_decision", run_id=rev.run_id, input_event=rev.event_id, mode="human",
            outcome=decision, recommendation=decision,
            reasoning_steps=[f"{role} decided: {decision}", f"Comment: {comment}", f"On: {rev.summary}"],
            pipeline_nodes=["P"], readiness_dimensions=["human_interaction_supervision"],
            requires_human_decision=False,
        )
        rev.decision = {"decision": decision, "reviewer_role": role, "comment": comment, "audit_id": entry.audit_id}
        run = self.runs.get(rev.run_id)
        if run:
            self.emit(run, "review_recorded", {"review_id": review_id, "event_id": rev.event_id, **rev.decision})
        return rev, entry.audit_id


engine = Engine()
