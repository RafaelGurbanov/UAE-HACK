from app.api.deps import get_audit
from app.core.taxonomy import AgentId, PipelineNode, ReadinessDimension


def test_taxonomy_has_all_nodes_and_dimensions(client):
    body = client.get("/api/meta/taxonomy").json()
    assert [n["id"] for n in body["pipeline_nodes"]] == ["SRC", "C", "PP", "M", "P", "D", "SINK"]
    assert len(body["readiness_dimensions"]) == 8


def test_scenarios_listed_from_yaml(client):
    ids = [s["id"] for s in client.get("/api/scenarios").json()]
    assert {"inapp_purchases_escalation", "false_positive_controversy"} <= set(ids)


def test_validation_error_envelope(client):
    r = client.post("/api/ask", json={"question": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_sources_and_unknown_law(kb_with_doc, client):
    body = client.get("/api/sources").json()
    assert body["total_documents"] == 1 and body["documents"][0]["chunk_count"] == 6
    assert client.get("/api/laws/nope").status_code == 404


def test_audit_roundtrip_and_export(client):
    get_audit().log(kind="agent", agent=AgentId.DATA_PROTECTION, input_event="evt_test",
                    reasoning_steps=["retrieved 0 chunks"], pipeline_nodes=[PipelineNode.D],
                    readiness_dimensions=[ReadinessDimension.HUMAN_SUPERVISION], requires_human_decision=True)
    body = client.get("/api/audit", params={"agent": "data_protection"}).json()
    assert body["total"] == 1 and body["entries"][0]["pipeline_nodes"] == ["D"]
    r = client.get("/api/audit/export", params={"format": "jsonl"})
    assert r.status_code == 200 and r.text.count("\n") == 1
