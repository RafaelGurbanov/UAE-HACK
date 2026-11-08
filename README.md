# Qalam Policy Command Centre

AI legal and policy advisory platform for the UAE, built for the **ITU AI for Good Lab Hackathon: United Arab Emirates (8 Dec 2026)**.
It is the governance layer around a smart-pen learning-difficulty screening service:
- specialist regulator agents and a Coordinator
- progressive scenario simulation
- policy-gap analysis against global examples
- a full audit trail

Everything is mapped to **ITU-T Y.3172** and the **ITU AI Readiness** dimensions.

> Informational only, not legal advice. The official Arabic text of UAE legislation prevails. All student data is synthetic.

## Status
Live mode works end to end:
- **Ask a question:** language detection, then EN+AR query rewrite, then hybrid retrieval (bge-m3 in Chroma, plus BM25, plus a reranker).
- **No supporting source:** below the score threshold the system refuses, without calling the model.
- **Answer:** Claude generates the answer, the citations are checked against the retrieved text, everything is audit-logged, and the answer streams over SSE.

Frontend: legal search, pipeline map and citation drawer (live and mock). Scenario room, gap board and audit pages are next.

## Two answer modes
| | **Offline (free, default)** | **LLM** |
|---|---|---|
| Needs | nothing | `ANTHROPIC_API_KEY` |
| Answers come from | `kb/data/*.json` entries, shown word for word; otherwise matching document passages, verbatim | Claude, from retrieved passages, with every quote checked |
| LLM calls | **none** | yes |
| Switch | `LLM_PROVIDER=offline`, or `auto` with no key | `LLM_PROVIDER=anthropic` and a key |

In offline mode every answer is one of these:
- **Matched entry:** a `kb/data` entry, labelled "Answered from knowledge base data (no AI generation)".
- **Passage:** one to three verbatim document passages, labelled "Passage from source document".
- **Guidance:** a short how-to message for greetings and small talk.
- **No source:** "No supporting source found in the knowledge base".

Badges say **Verified** only when that citation has `verified: true`; otherwise they say "Source to be verified". To add or edit answers, see `kb/data/README.md` and run `.\scripts\validate-data.ps1`.

## Quick start (Windows, PowerShell)
Run these from the project folder (the one with this README). You need **Python 3.12** (or 3.11) and **Node.js 22 LTS**.

**Shortcut:** double-click `run-website.cmd` in the project folder. It runs setup the first time, then starts the backend and website and opens the site.

| Step | Command |
|---|---|
| 1. Install everything (once; several minutes) | `.\scripts\setup.ps1` |
| 2. (Optional, LLM mode only) Add your key | open `.env`, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...`. Skip this step for the free offline mode. |
| 3. Put documents in the KB | copy PDF / HTML / TXT files to `kb\raw\uae_federal\`, `kb\raw\emirate\` or `kb\raw\global_example\` |
| 4. Index them | `.\scripts\ingest.ps1` (first run downloads bge-m3, about 2.3 GB) |
| 5. Start backend + website | `.\scripts\start-all.ps1`, then go to http://localhost:5173 |
| 6. Test 10 questions | `.\scripts\eval.ps1`, writes `kb\eval\report.md` |

If PowerShell says *"running scripts is disabled"*, run this once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Or prefix each command with `powershell -ExecutionPolicy Bypass -File`, for example `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`.

To start the two parts separately: `.\scripts\start-backend.ps1` (API at http://localhost:8000/docs) and `.\scripts\start-frontend.ps1`.

**Adding a document from a URL** (official sources only). It downloads into `kb\raw` and registers the document in `kb\sources.csv` with `verified=false`:
```powershell
.\scripts\add-source.ps1 https://<official-url> --title "Exact official title" --layer uae_federal --language ar --status in_force
.\scripts\ingest.ps1
```
Files you copy into `kb\raw` by hand are registered automatically on ingest, with status `unknown`, verified `false` and the note "SOURCE TO BE VERIFIED". Fill in title, law number, year, status and URL in `kb\sources.csv` afterwards and run ingest again.

**What the website shows:**
- **Answered:** a verified answer. Its badges say "Verified" only when `verification.passed` is true.
- **No supporting source:** a plain refusal, with no model call.
- **Backend not reachable, AI model not configured, or knowledge base empty:** a card with the exact command to fix it.
- **General AI answer (toggle):** a labelled answer, "Not from the knowledge base, not a legal source". It has no citations, and the audit log records it as `mode=general`.

**Without the big model downloads:** set `RERANKER_ENABLED=false` to skip the reranker; the no-source decision then uses `MIN_DENSE_SCORE`. Or use Ollama with `EMBEDDING_PROVIDER=ollama` (after `ollama pull bge-m3`).

## Layout
```
backend/    FastAPI (Python 3.11): app/{api,agents,orchestrator,kb,scenarios,audit,llm,core}
frontend/   React 18 + Vite + TS (strict): src/{components,pages,hooks,lib,styles}
kb/         sources.csv, sources_todo.md, raw/, processed/, eval/
scenarios/  *.yaml (progressive events, who sees what)
docs/       architecture.md, api.md, y3172_mapping.md, gap_analysis.md
```

## Run
```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt        # + requirements-ml.txt from Phase 2
cp .env.example .env                   # set LLM_PROVIDER and keys
uvicorn app.main:app --reload          # http://localhost:8000/docs
pytest

# frontend
cd frontend && npm install && cp .env.example .env
npm run dev          # against backend
npm run dev:mock     # mock mode, no backend needed
npm test && npm run build

# both
docker compose up --build
```

## Run the website (frontend)
All commands are run from this folder (`dubai`). You need Node.js 20+ (22 recommended).

```bash
cd frontend
npm install                 # first time only

npm run dev                 # live mode (default): talks to the backend at VITE_API_URL
npm run dev:mock            # mock demo: no backend needed -> http://localhost:5173
npm test                    # component tests (Vitest)
npm run lint                # ESLint
npm run typecheck           # TypeScript strict
npm run build:demo          # static mock-mode site in frontend/dist (what we deploy)
npm run preview             # serve the built site locally -> http://localhost:4173
```

- **Mock mode** (`VITE_MOCK=true`) uses local fixtures only. Every legal reference in it reads "Demo placeholder, source to be verified", and a "Demo data" badge is always visible.
- **Live mode** (`VITE_MOCK=false`, the default) calls the FastAPI backend described in `docs/api.md`. The site never holds API keys and never calls an LLM.
- **Base path:** set `VITE_BASE=/<repo-name>/` before building for GitHub Pages; leave it as `/` for Vercel, Netlify or Docker.

Deployment and the demo-recording script are added in Phase 6.

## Tests

```powershell
# backend unit + API tests (no key, no network)
backend\.venv\Scripts\python -m pytest backend -q
# frontend unit tests
cd frontend; npm test; cd ..
# end-to-end browser tests: start the site first (run-website.cmd), then in a second window
backend\.venv\Scripts\python -m pip install playwright
backend\.venv\Scripts\python -m playwright install chromium
backend\.venv\Scripts\python -m pytest e2e -q
```

The end-to-end suite (`e2e/test_site.py`) drives a real browser against http://localhost:5173 in
offline mode: every route loads with no console errors, no horizontal scroll at 360 px, search
(answered, no source, greetings, short input, Arabic, Azerbaijani, topic chips, citation drawer
with Escape), laws, both scenarios with a human decision, gap filters and radar, audit filters and
JSON export, EN/AR switch with RTL, theme persistence and keyboard focus.
Set `BASE_URL` to test another address, or `E2E_CHROME` to use an installed Chrome/Edge instead of
downloading Chromium.

## Switching the LLM (ITU sandbox / open models)
One variable, `LLM_PROVIDER`, in `backend/.env`:

| Value | Use | Extra vars |
|---|---|---|
| `anthropic` (default) | Claude | `ANTHROPIC_API_KEY`, `LLM_MODEL`, `LLM_ROUTER_MODEL` |
| `openai_compat` | Ollama, vLLM, ITU sandbox, any `/chat/completions` endpoint | `OPENAI_COMPAT_BASE_URL`, `OPENAI_COMPAT_API_KEY`, `LLM_MODEL` |
| `mock` | tests, offline demo | none |

A new provider is one class implementing `complete()` and `stream()` (`backend/app/llm/base.py`). Grounding does not depend on the provider: retrieval and citation verification run in our own code.

## Evaluation (filled in Phase 2–3)
| Metric | Value |
|---|---|
| Retrieval hit rate @8 (50+ EN/AR questions) | – |
| Citation accuracy (verified / emitted) | – |
| Refusal-when-no-source rate | – |
