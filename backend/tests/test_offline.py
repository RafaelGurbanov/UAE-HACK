import json

import pytest

ASK = "/api/ask"


def ask(client, q, **kw):
    r = client.post(ASK, json={"question": q, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_greeting_returns_guidance(offline, client):
    body = ask(client, "hello")
    assert body["mode"] == "guidance" and body["outcome"] == "guidance"
    assert "knowledge base" in body["answer"]["short_answer"] and body["answer"]["legal_basis"] == []
    assert ask(client, "salam")["mode"] == "guidance"
    assert ask(client, "مرحبا")["mode"] == "guidance"


def test_off_topic_is_no_source_with_exact_text(offline, client):
    body = ask(client, "weather in Paris")
    assert body["mode"] == "no_source" and body["outcome"] == "no_source"
    assert body["no_source_message"] == "No supporting source found in the knowledge base"
    assert body["suggested_topics"]


def test_ads_question_matches_advertising_entry(offline, client):
    body = ask(client, "Can an app show ads to minors?")
    assert body["mode"] == "offline_json" and body["matched_entry"] == "advertising-to-minors"
    assert "Answered from knowledge base data (no AI generation)" in body["answer"]["status_and_limits"]


@pytest.mark.parametrize("q", [
    "ما الموافقة المطلوبة لمعالجة البيانات الشخصية للطفل؟",
    "هل يلزم إذن الوالدين لجمع بيانات الأطفال؟",
    "Uşağın şəxsi məlumatlarını emal etmək üçün hansı razılıq lazımdır?",
    "Uşaqların məlumatlarını toplamaq üçün valideyn icazəsi lazımdırmı?",
])
def test_arabic_and_azerbaijani_paraphrases_match_consent(offline, client, q):
    body = ask(client, q)
    assert body["matched_entry"] == "children-data-consent", body
    assert body["language"] in {"ar", "az"}


def test_unverified_entry_never_reports_verified(offline, client):
    body = ask(client, "What consent is required to process a child's personal data?")
    cits = body["answer"]["legal_basis"]
    assert cits and all(c["verified"] is False for c in cits)
    assert all(c["title"] == "SOURCE TO BE VERIFIED" for c in cits)
    assert body["verification"]["passed"] is False


def test_general_mode_is_refused_offline(offline, client):
    body = ask(client, "Explain dyslexia", mode="general")
    assert body["mode"] == "guidance" and "never calls" in body["answer"]["short_answer"]


def test_extractive_fallback_returns_verbatim_passage(kb_with_doc, offline, client):
    body = ask(client, "What administrative fine applies under the competent authority?")
    assert body["mode"] == "extractive" and body["outcome"] == "answered"
    p = body["answer"]["legal_basis"][0]
    chunk = next(json.loads(x) for x in (kb_with_doc / "processed" / "demo-act.jsonl").read_text(encoding="utf-8")
                 .splitlines() if json.loads(x)["chunk_id"] == p["chunk_id"])
    assert p["quote"] == chunk["text"] and p["article"] == "5"  # verbatim, not generated
    assert p["verified"] is False
    assert "Passage from source document" in body["answer"]["short_answer"]


def test_every_query_is_audited(offline, client):
    ask(client, "hello")
    ask(client, "Can an app show ads to minors?")
    ask(client, "weather in Paris")
    entries = client.get("/api/audit").json()["entries"]
    by_mode = {e["mode"]: e for e in entries}
    assert set(by_mode) == {"guidance", "offline_json", "no_source"}
    hit = by_mode["offline_json"]
    assert hit["matched_entry"] == "advertising-to-minors" and hit["score"] >= 0.45
    assert hit["retrieved_chunks"][0]["chunk_id"] == "data:advertising-to-minors"
    assert hit["llm"]["llm_calls"] == 0


def test_sse_stream_offline(offline, client):
    r = client.post(ASK + "?stream=true", json={"question": "Can an app show ads to minors?"})
    text = r.text.replace("\r\n", "\n")
    assert "event: retrieval" in text and "event: final" in text and "event: token" not in text


def test_health_reports_offline(offline, client):
    h = client.get("/api/health").json()
    assert h["answer_mode"] == "offline" and h["llm_provider"] == "offline" and h["data_entries"] == 8
    assert h["llm_configured"] is True and h["data_errors"] == []


def test_auto_provider_without_key_is_offline(monkeypatch):
    from app.core.config import Settings

    assert Settings(llm_provider="auto", anthropic_api_key="").effective_provider == "offline"
    assert Settings(llm_provider="anthropic", anthropic_api_key="").offline
    assert Settings(llm_provider="auto", anthropic_api_key="sk-x").effective_provider == "anthropic"
