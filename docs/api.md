# API contract (v0.3)

> **v0.3 changes (live mode):**
> - `POST /ask` now runs the real pipeline. The request gains `mode: "grounded" | "general"` (default `grounded`). The response gains `mode`, and `outcome` can also be `"general"`: no retrieval, no citations, `verification: null`, labelled "Not from the knowledge base, not a legal source", and logged with `mode=general`.
> - `VerificationReport.passed` (bool): true only if at least one citation survived and none failed. The UI shows "Verified" only when it is true. If no citation survives verification, the outcome becomes `no_source`.
> - The SSE `retrieval` event also carries `best_score` and `threshold`. Lines end in `\r\n` (sse-starlette), and `: ping` comments arrive every 15 s.
> - Errors before streaming starts: `503 llm_unavailable` (missing or invalid key, unknown model) and `409 kb_empty` (nothing ingested). Errors after streaming has started arrive as an `error` event with the same `{code, message}`.
> - `GET /health` gains `llm_configured`, `embedding_provider`, `embedding_model`, `index_chunks` and `problems[]`.
> - `GET /laws/{doc_id}` is built from `kb/processed/<doc_id>.jsonl`.
> - `GET /audit` supports the `node` and `requires_human` filters. Entries gain `mode` and `outcome`.

## API contract history: v0.2

> **v0.2 changes (frontend Phase 1, confirmed against `architecture.md`):**
> 1. `GET /audit` gains two filters: `node` (`PipelineNode`, which matches entries whose `pipeline_nodes` contain it) and `requires_human` (bool). The audit terminal filters by agent, node and result. **Backend: still to add (frontend Phase 6).**
> 2. `Citation.url` may be `""` when no verified link exists. The UI then hides the link instead of rendering `#`.
> 3. A second scenario id is reserved for the controversy case: `false_positive_controversy`. Its YAML is pending in the backend.
> 4. Mock mode (`VITE_MOCK=true`) implements this exact contract in `frontend/src/lib/mock/client.ts`. Every legal reference in it is labelled "Demo placeholder, source to be verified".

Base URL: `${VITE_API_URL}/api` (default `http://localhost:8000/api`). Interactive OpenAPI docs live at `/docs`.
The source of truth is `backend/app/api/schemas.py`. `frontend/src/lib/types.ts` mirrors it. Change the backend first, then this doc, then the TS types.

**Conventions**
- JSON in and out, UTF-8. Arabic text is returned as-is (no transliteration).
- Times are ISO 8601 UTC.
- IDs: `doc_id` is a slug (e.g. `uae-fdl-<no>-<year>-<topic>-ar`). `chunk_id` = `<doc_id>:art-<n>[:<part>]`. Audit IDs start with `aud_`, runs with `run_`, reviews with `rev_`.
- Every error uses one envelope:
  ```json
  { "error": { "code": "not_found", "message": "Unknown doc_id 'x'", "details": null } }
  ```
  Codes: `validation_error` (422), `not_found` (404), `not_implemented` (501, stubs only), `llm_unavailable` (503), `internal` (500).
- Auth: none (hackathon). LLM keys live only in the backend `.env`. The frontend never calls an LLM.
- CORS origins come from `CORS_ORIGINS`.

**Shared enums** (also served by `GET /api/meta/taxonomy`)

| Enum | Values |
|---|---|
| `PipelineNode` | `SRC` `C` `PP` `M` `P` `D` `SINK` |
| `ReadinessDimension` | `open_data_open_source`, `generative_ai_content_ecosystem`, `contextualisation_regional_development`, `domain_integration_cross_domain`, `human_interaction_supervision`, `ai_policy_implementation`, `ai_social_inclusion`, `digital_infrastructure_energy` |
| `KBLayer` | `uae_federal`, `emirate`, `global_example` |
| `LegalStatus` | `in_force`, `amended`, `repealed`, `not_legislation`, `unknown` |
| `AgentId` | `legal_adviser`, `data_protection`, `education`, `consumer_protection`, `ai_ethics`, `coordinator`, `gap_analyst` |
| `GapType` | `unclear_responsibility`, `missing_standard`, `legislative_gap`, `coordination_problem`, `objective_conflict` |
| `Domain` | `children_data`, `consent`, `education`, `in_app_purchases`, `advertising_minors`, `cross_border_transfer`, `automated_decisions`, `disability_inclusion`, `cybersecurity`, `ai_ethics` |

---

## Endpoint summary

| Method | Path | Phase | Purpose |
|---|---|---|---|
| GET | `/health` | 1 ✅ | Liveness, provider, KB and audit counts |
| GET | `/meta/taxonomy` | 1 ✅ | Enums with display labels *(addition)* |
| GET | `/sources` | 1 ✅ / 2 | Source list + coverage matrix |
| GET | `/laws/{doc_id}` | 2 | Full law, article by article |
| POST | `/ask` | 3 | Legal Q&A (JSON, or SSE with `?stream=true`) |
| GET | `/scenarios` | 1 ✅ | List scenarios *(addition)* |
| POST | `/scenarios/{id}/start` | 5 | Create a run |
| GET | `/scenarios/{id}/stream?run_id=` | 5 | SSE stream of run activity |
| POST | `/scenarios/{id}/next` | 5 | Release the next event |
| POST | `/reviews/{review_id}/decision` | 4 | Human-in-the-loop decision *(addition)* |
| GET | `/gaps` | 6 | Structured policy gaps + radar data |
| GET | `/audit` | 1 ✅ | Filterable audit entries |
| GET | `/audit/export` | 1 ✅ | Download the log (jsonl/json) |

✅ = working now. Other endpoints return `501 not_implemented` until their phase ships.

---

## GET /health
```json
{ "status": "ok", "version": "0.1.0", "llm_provider": "anthropic", "llm_model": "claude-sonnet-5-5",
  "kb_documents": 12, "kb_chunks": 1840, "audit_entries": 37 }
```
`status: "degraded"` means the LLM or vector store is unreachable. Search and refusal still work; generation does not.

## GET /meta/taxonomy
Returns `pipeline_nodes` and `readiness_dimensions` as `[{id, label}]`, plus `layers`, `gap_types`, `domains`, `agents` as string arrays. The UI uses these for labels, tooltips and filters.

## GET /sources
Query: `layer`, `status`, `language` (`en|ar`), all optional.
```json
{
  "documents": [{
    "doc_id": "uae-pdp-ar", "title": "…", "title_ar": "…", "issuing_body": "…",
    "law_number": "…", "year": 0, "status": "in_force", "layer": "uae_federal", "language": "ar",
    "translation_of": null, "amends": [], "amended_by": [], "domains": ["children_data","consent"],
    "url": "https://…", "retrieved_at": "2026-11-10", "verified": true, "chunk_count": 48
  }],
  "coverage": [{ "layer": "uae_federal", "domain": "children_data", "documents": 3 }],
  "total_documents": 12, "total_chunks": 1840
}
```
English translations set `translation_of` to the Arabic `doc_id`. The Arabic text is authoritative.

## GET /laws/{doc_id}
```json
{
  "document": { "…SourceDocument…": "" },
  "articles": [{ "article": "7", "heading": "…", "chapter": "2", "text": "…", "chunk_ids": ["uae-pdp-ar:art-7"], "amended": false }],
  "translations": ["uae-pdp-en"]
}
```
404 if the `doc_id` is unknown.

## POST /ask
Request:
```json
{
  "question": "What consent is required to process a child's personal data?",
  "language": "en",
  "conversation_id": "conv_…",
  "agent": "legal_adviser",
  "filters": { "layers": ["uae_federal","emirate"], "include_repealed": false, "domains": [] }
}
```
- `language` is optional and auto-detected (Arabic script → `ar`).
- `conversation_id` is optional. Send it back to keep follow-up context. Retrieval re-runs on every turn.
- `filters.layers` defaults to UAE layers only. `global_example` is used for gap analysis, not for answering "what does UAE law say".

Response `200` (`outcome: "answered"`):
```json
{
  "answer_id": "ans_…", "conversation_id": "conv_…", "outcome": "answered", "language": "en",
  "answer": {
    "short_answer": "… [c1] …",
    "legal_basis": [{
      "id": "c1", "chunk_id": "uae-pdp-ar:art-7", "doc_id": "uae-pdp-ar", "title": "…",
      "law_number": "…", "year": 0, "article": "7", "clause": "2", "quote": "<exact substring of chunk>",
      "url": "https://…", "layer": "uae_federal", "status": "in_force", "language": "ar",
      "score": 0.81, "verified": true
    }],
    "details": "… [c1] …",
    "status_and_limits": "In force. Not found in KB: …",
    "related": ["…"],
    "disclaimer": "Informational only, not legal advice. The official Arabic text prevails."
  },
  "no_source_message": null, "suggested_topics": [],
  "pipeline_nodes": ["D","SINK"], "readiness_dimensions": ["human_interaction_supervision"],
  "verification": { "checked": 3, "verified": 3, "removed": [], "warnings": [] },
  "requires_human_decision": false,
  "audit_id": "aud_…"
}
```
Response `200` (`outcome: "no_source"`, when the best rerank score is below `RETRIEVAL_MIN_SCORE`):
```json
{ "outcome": "no_source", "answer": null,
  "no_source_message": "No supporting source found in the knowledge base.",
  "suggested_topics": ["Children's data","Consent"], "audit_id": "aud_…", "…": "" }
```
**Guarantees.** `legal_basis[].quote` is an exact substring of the chunk text. `verified` is set by the checker, never by the LLM. Unverifiable claims are removed and listed in `verification.removed`. Repealed text is never returned as current. A citation never combines two laws.

**Streaming** (`POST /ask?stream=true`, `Accept: text/event-stream`). Read it with `fetch` and a stream reader, because `EventSource` cannot POST. Events in order:

| `event:` | `data:` |
|---|---|
| `retrieval` | `{ "chunks": [{chunk_id, doc_id, article, score}] }` |
| `token` | `{ "text": "…" }` (repeated) |
| `verification` | `VerificationReport` |
| `final` | full `AskResponse` (verified; the UI **replaces** the streamed draft with it) |
| `error` | error body |

Streamed tokens are an unverified draft. The UI shows them dimmed until `final` arrives.

## Scenarios

### GET /scenarios
`[{ "id", "title", "description", "controversial": bool, "total_events": int }]`

### POST /scenarios/{id}/start
`{ "run_id": "run_…", "scenario": ScenarioSummary, "stream_url": "/api/scenarios/{id}/stream?run_id=run_…" }`

### GET /scenarios/{id}/stream?run_id=…  (SSE, `EventSource`)
Each message is `data: StreamEnvelope`:
```json
{ "type": "agent_assessment", "run_id": "run_…", "seq": 14, "ts": "2026-…Z", "data": { } }
```
| `type` | `data` |
|---|---|
| `run_started` | `{ scenario }` |
| `event_released` | `ScenarioEvent` `{id, step, at, title, description, severity, visible_to[], pipeline_nodes[]}` |
| `agent_status` | `{ agent, state: "idle" \| "thinking" \| "done" \| "error" }` |
| `agent_step` | `{ agent, step: "Retrieved 6 chunks on consent" }` (reviewable reasoning summary, not raw chain-of-thought) |
| `agent_assessment` | `AgentAssessment` `{agent, summary, recommendation, confidence, citations[], pipeline_nodes[], readiness_dimensions[], requires_human_decision, audit_id}` |
| `conflict_detected` | `Conflict` `{agents[], topic, description}` |
| `coordinator_recommendation` | `{recommendation, actions[], conflicts[], requires_human_decision, review_id, citations[], audit_id}` |
| `human_review_required` | `{ review_id, summary, options: ["approve","override","escalate"] }` |
| `pipeline_highlight` | `{ nodes: PipelineNode[], severity }` (drives the pipeline map) |
| `run_completed` | `{ summary }` |
| `error` | error body |

`seq` increases monotonically per run. On reconnect, the client sends `Last-Event-ID`, and the server replays from that `seq`.

### POST /scenarios/{id}/next
Request `{ "run_id": "run_…" }` → `{ "run_id", "released": ScenarioEvent | null, "remaining": 2 }`. Agents react asynchronously, and their output arrives on the stream.

## POST /reviews/{review_id}/decision  *(addition for the human-in-the-loop panel)*
```json
{ "decision": "approve", "reviewer_role": "counsellor", "comment": "Reviewed with school psychologist." }
```
→ `{ "review_id", "decision", "audit_id" }`. Every decision is written to the audit log (`kind: "human_decision"`).

## GET /gaps
Query: `gap_type`, `domain`, both optional.
```json
{
  "gaps": [{
    "id": "gap_…", "title": "…", "gap_type": "legislative_gap", "domain": "advertising_minors",
    "uae_says":            { "statement": "…", "citations": [Citation] },
    "global_example_says": { "statement": "…", "citations": [Citation] },
    "gap_analysis": "ANALYSIS (not law): …",
    "recommendation": "…", "severity": "high",
    "pipeline_nodes": ["M","D","SINK"], "readiness_dimensions": ["ai_policy_implementation"],
    "audit_id": "aud_…"
  }],
  "readiness_radar": { "human_interaction_supervision": 0.6, "…": 0 }
}
```

## Audit

### GET /audit
Query: `agent`, `run_id`, `kind`, `node`, `requires_human`, `since` (ISO), `limit` (1–5000, default 200). Results are newest first.
```json
{ "total": 1, "entries": [{
  "audit_id": "aud_…", "timestamp": "…", "kind": "agent", "agent": "data_protection", "run_id": "run_…",
  "input_event": "e4_inferred_disability_ads",
  "retrieved_chunks": [{ "chunk_id": "…", "doc_id": "…", "article": "7", "url": "…", "score": 0.78 }],
  "reasoning_steps": ["…"], "recommendation": "…", "citations": ["<chunk_id>"], "confidence": 0.8,
  "pipeline_nodes": ["M","D"], "readiness_dimensions": ["ai_social_inclusion"],
  "requires_human_decision": true,
  "llm": { "provider": "anthropic", "model": "…", "input_tokens": 0, "output_tokens": 0, "latency_ms": 0 }
}]}
```
`kind` ∈ `ask | agent | coordinator | gap | scenario_event | human_decision | system`.

### GET /audit/export?format=jsonl|json&run_id=
Returns a file download (`Content-Disposition: attachment`). `jsonl` gives one `AuditEntry` per line.
