"""Runtime settings. Read from the repo-root .env (single config file), then
backend/.env if present, then real environment variables (highest priority)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", REPO_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["dev", "test", "prod"] = "dev"
    app_version: str = "0.3.0"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"

    # --- LLM (one switch: LLM_PROVIDER) ---------------------------------
    # auto     -> anthropic when ANTHROPIC_API_KEY is set, otherwise offline
    # offline  -> FREE: answers only from kb/data/*.json + verbatim document passages; never calls an LLM
    llm_provider: Literal["auto", "offline", "anthropic", "openai_compat", "mock"] = "auto"
    llm_model: str = "claude-sonnet-5-5"          # answers
    llm_router_model: str = "claude-haiku-5-5"    # query rewrite / expansion
    anthropic_api_key: str = ""
    openai_compat_base_url: str = "http://localhost:11434/v1"
    openai_compat_api_key: str = "ollama"
    llm_timeout_s: float = 90.0
    llm_max_tokens: int = 1800

    # --- Embeddings / retrieval -----------------------------------------
    embedding_provider: Literal["sentence_transformers", "ollama", "hash"] = "sentence_transformers"
    embedding_model: str = "BAAI/bge-m3"
    ollama_base_url: str = "http://localhost:11434"
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    retrieval_top_k: int = 8
    retrieval_candidates: int = 30
    # no_source thresholds (calibrate with `python -m app.kb.evaluate`)
    min_rerank_score: float = 0.15   # bge-reranker sigmoid score of the best passage
    min_dense_score: float = 0.45    # cosine of the best passage when the reranker is off

    # --- Offline JSON mode ------------------------------------------------
    offline_min_score: float = 0.45      # weighted query-term coverage of the best JSON entry
    extractive_min_score: float = 0.6    # coverage of the best document passage for the extractive fallback
    offline_dense: Literal["auto", "on", "off"] = "auto"  # auto = use bge-m3 only if already downloaded
    scenario_step_delay: float = 0.35    # seconds between agent steps in the scenario room (0 = instant)

    # --- Paths -----------------------------------------------------------
    kb_dir: Path = REPO_ROOT / "kb"
    data_dir: Path = REPO_ROOT / "kb" / "data"
    gaps_dir: Path = REPO_ROOT / "kb" / "gaps"
    index_dir: Path = REPO_ROOT / "kb" / "index" / "chroma"
    scenarios_dir: Path = REPO_ROOT / "scenarios"
    audit_log_path: Path = REPO_ROOT / "backend" / "data" / "audit.jsonl"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_provider(self) -> str:
        """auto, or anthropic without a key, means offline: the free mode never needs an API key."""
        if self.llm_provider in ("auto", "anthropic") and not self.anthropic_api_key.strip():
            return "offline"
        if self.llm_provider == "auto":
            return "anthropic"
        return self.llm_provider

    @property
    def offline(self) -> bool:
        return self.effective_provider == "offline"

    @property
    def llm_configured(self) -> bool:
        """True when the effective mode can answer (offline needs no key)."""
        return True if self.offline else (self.effective_provider != "anthropic" or bool(self.anthropic_api_key.strip()))


@lru_cache
def get_settings() -> Settings:
    return Settings()
