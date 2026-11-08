import os
import shutil
from pathlib import Path

import pytest

os.environ["LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "test"
os.environ["EMBEDDING_PROVIDER"] = "hash"
FIXTURES = Path(__file__).parent / "fixtures"


def _reset_caches():
    from app.api import deps
    from app.core.config import get_settings
    from app.kb import embeddings, index
    from app.llm import get_llm

    get_settings.cache_clear()
    deps.get_audit.cache_clear()
    embeddings.get_embedder.cache_clear()
    embeddings.get_reranker.cache_clear()
    get_llm.cache_clear()
    index._index = None


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch):
    """Every test gets its own kb/, index and audit log."""
    kb = tmp_path / "kb"
    (kb / "raw" / "uae_federal").mkdir(parents=True)
    (kb / "processed").mkdir()
    monkeypatch.setenv("KB_DIR", str(kb))
    monkeypatch.setenv("INDEX_DIR", str(kb / "index" / "chroma"))
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("SCENARIOS_DIR", str(Path(__file__).parents[2] / "scenarios"))
    monkeypatch.setenv("DATA_DIR", str(Path(__file__).parents[2] / "kb" / "data"))  # the real seed entries
    monkeypatch.setenv("OFFLINE_DENSE", "off")
    monkeypatch.setenv("GAPS_DIR", str(Path(__file__).parents[2] / "kb" / "gaps"))
    _reset_caches()
    yield kb
    _reset_caches()


@pytest.fixture
def kb_with_doc(isolated: Path) -> Path:
    shutil.copy(FIXTURES / "demo_act.txt", isolated / "raw" / "uae_federal" / "demo_act.txt")
    from app.kb import ingest

    assert ingest.main([]) == 0
    return isolated


@pytest.fixture
def fake_llm(monkeypatch):
    from tests.fakes import SourceQuotingLLM

    llm = SourceQuotingLLM()
    monkeypatch.setattr("app.agents.legal_adviser.get_llm", lambda: llm)
    monkeypatch.setattr("app.api.routes.ask.get_llm", lambda: llm)
    return llm


@pytest.fixture
def offline(monkeypatch):
    """Offline JSON mode, with any LLM call turned into a test failure."""
    monkeypatch.setenv("LLM_PROVIDER", "offline")
    _reset_caches()

    def no_llm(*a, **k):
        raise AssertionError("offline mode must never call an LLM")

    monkeypatch.setattr("app.agents.legal_adviser.get_llm", no_llm)
    monkeypatch.setattr("app.api.routes.ask.get_llm", no_llm)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
