import json


def _sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        ev = data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
        if ev and data:
            out.append((ev, json.loads(data)))
    return out


def test_answer_is_grounded_and_verified(kb_with_doc, fake_llm, client):
    r = client.post("/api/ask", json={"question": "What consent is needed to process a child's personal data?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "answered" and body["mode"] == "grounded"
    assert body["verification"]["passed"] is True
    c = body["answer"]["legal_basis"][0]
    assert c["verified"] and c["doc_id"] == "demo-act" and c["article"] == "2"
    assert body["pipeline_nodes"] == ["SRC", "P"]  # BOGUS node dropped
    assert body["requires_human_decision"] is True
    assert "not yet human-verified" in body["answer"]["status_and_limits"]
    assert fake_llm.calls == ["complete", "stream"]
    audit = client.get("/api/audit").json()["entries"][0]
    assert audit["mode"] == "grounded" and audit["outcome"] == "answered" and audit["retrieved_chunks"]


def test_unverifiable_quote_turns_into_no_source(kb_with_doc, fake_llm, client):
    fake_llm.bad_quote = True
    body = client.post("/api/ask", json={"question": "What consent is needed to process a child's personal data?"}).json()
    assert body["outcome"] == "no_source"
    assert body["verification"]["passed"] is False and body["verification"]["removed"]


def test_off_topic_question_is_refused_without_generation(kb_with_doc, fake_llm, client):
    body = client.post("/api/ask", json={"question": "Who won the football world cup in 2022?"}).json()
    assert body["outcome"] == "no_source"
    assert body["no_source_message"] == "No supporting source found in the knowledge base"
    assert "stream" not in fake_llm.calls  # no answer generated without a source


def test_sse_stream_order(kb_with_doc, fake_llm, client):
    r = client.post("/api/ask?stream=true", json={"question": "Can a child's data be used for targeted advertising?"})
    events = _sse(r.text)
    names = [e for e, _ in events]
    assert names[0] == "retrieval" and "token" in names and names[-2:] == ["verification", "final"]
    streamed = "".join(d["text"] for e, d in events if e == "token")
    assert "<" not in streamed and "[c1]" in streamed  # only the short answer is streamed, no tags
    assert events[-1][1]["outcome"] == "answered"


def test_general_mode_has_no_citations_and_is_logged(kb_with_doc, fake_llm, client):
    body = client.post("/api/ask", json={"question": "Explain dyslexia briefly", "mode": "general"}).json()
    assert body["outcome"] == "general" and body["answer"]["legal_basis"] == []
    assert body["verification"] is None
    assert "Not from the knowledge base" in body["answer"]["status_and_limits"]
    assert client.get("/api/audit").json()["entries"][0]["mode"] == "general"


def test_anthropic_without_key_falls_back_to_offline(client, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    body = client.post("/api/ask", json={"question": "Can an app show ads to minors?"}).json()
    assert body["mode"] == "offline_json"


def test_llm_failure_gives_clear_error(client, monkeypatch):
    def broken():
        raise RuntimeError("The LLM provider rejected the API key.")

    monkeypatch.setattr("app.api.routes.ask.get_llm", broken)
    r = client.post("/api/ask", json={"question": "anything at all"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "llm_unavailable"


def test_empty_kb_error(fake_llm, client):
    r = client.post("/api/ask", json={"question": "anything at all"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "kb_empty"


def test_health_reports_problems(client):
    body = client.get("/api/health").json()
    assert body["status"] == "degraded" and body["index_chunks"] == 0
    assert any("Knowledge base is empty" in p for p in body["problems"])


def test_law_view_from_processed_chunks(kb_with_doc, client):
    law = client.get("/api/laws/demo-act").json()
    assert [a["article"] for a in law["articles"]][1:4] == ["1", "2", "3"]
