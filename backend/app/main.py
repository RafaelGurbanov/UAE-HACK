import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import ask, audit, gaps_data, kb, scenarios, system
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()
    log.info("Answer mode: %s", "OFFLINE (kb/data JSON + verbatim passages, no LLM calls)" if s.offline
             else f"LLM ({s.effective_provider} / {s.llm_model})")
    from app.kb.data_model import load_data

    r = load_data(s.data_dir)  # validate kb/data at startup; problems are logged and shown in /api/health
    if r.errors:
        log.error("kb/data has %d problem(s). Run: python -m app.kb.validate_data", len(r.errors))
    yield


app = FastAPI(
    lifespan=lifespan,
    title="UAE AI Policy Command Centre API",
    version=settings.app_version,
    description="Governance layer for the smart-pen use case: legal search, agents, scenarios, gaps, audit. "
                "Informational only; not legal advice.",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {
        "code": "validation_error", "message": "Invalid request", "details": {"errors": exc.errors()}}})


for r in (system.router, kb.router, ask.router, scenarios.router, audit.router, gaps_data.router):
    app.include_router(r, prefix="/api")
