import json

import pytest


@pytest.fixture
def instant(monkeypatch):
    monkeypatch.setenv("SCENARIO_STEP_DELAY", "0")
    from app.core.config import get_settings

    get_settings.cache_clear()


def run_all(client, sid):
    run_id = client.post(f"/api/scenarios/{sid}/start").json()["run_id"]
    released = []
    while True:
        r = client.post(f"/api/scenarios/{sid}/next", json={"run_id": run_id})
        if r.status_code == 409:
            assert r.json()["error"]["code"] == "finished"
            break
        assert r.status_code == 200, r.text
        released.append(r.json()["released"]["id"])
    events = client.get(f"/api/scenarios/{sid}/runs/{run_id}").json()["events"]
    return run_id, released, events


def test_both_scenarios_listed(client):
    ids = {s["id"]: s for s in client.get("/api/scenarios").json()}
    assert ids["inapp_purchases_escalation"]["total_events"] == 4
    assert ids["false_positive_controversy"]["controversial"] is True


def test_escalation_runs_in_order_with_expected_handling(offline, instant, client):
    run_id, released, events = run_all(client, "inapp_purchases_escalation")
    assert released == ["e1_rollout", "e2_iap", "e3_monitoring", "e4_inferred_ads"]
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and events[-1]["type"] == "run_completed"
    # information asymmetry: data protection never sees the in-app purchase event
    dp = [e for e in events if e["type"] == "agent_assessment" and e["data"]["agent"] == "data_protection"]
    assert {e["data"]["event_id"] for e in dp} == {"e1_rollout", "e3_monitoring", "e4_inferred_ads"}
    final = [e for e in events if e["type"] == "coordinator_recommendation"][-1]["data"]
    assert [a.lower() for a in final["actions"]] == [x.lower() for x in final["expected_handling"]]
    assert any("AI ethics oversight" in a for a in final["actions"]) and final["requires_human_decision"]
    # e2: education (suspend) vs consumer (restrict) is a detected conflict
    conflicts = [e["data"] for e in events if e["type"] == "conflict_detected"]
    assert conflicts and set(conflicts[0]["agents"]) == {"education", "consumer_protection"}


def test_agent_without_source_says_so(offline, instant, client):
    _, _, events = run_all(client, "false_positive_controversy")
    ai = [e["data"] for e in events if e["type"] == "agent_assessment" and e["data"]["agent"] == "ai_ethics"][0]
    assert ai["no_source"] is True and "No supporting source found in the knowledge base" in ai["summary"]
    assert ai["citations"] == []
    edu = [e["data"] for e in events if e["type"] == "agent_assessment" and e["data"]["agent"] == "education"][0]
    assert edu["matched_entry"] == "counsellor-review" and all(c["verified"] is False for c in edu["citations"])


def test_next_after_end_and_unknown_run(offline, instant, client):
    run_all(client, "false_positive_controversy")
    r = client.post("/api/scenarios/false_positive_controversy/next", json={"run_id": "run_nope"})
    assert r.status_code == 404


def test_human_decision_recorded_and_audited(offline, instant, client):
    run_id, _, events = run_all(client, "false_positive_controversy")
    rev = [e["data"] for e in events if e["type"] == "human_review_required"][0]["review_id"]
    r = client.post(f"/api/reviews/{rev}/decision",
                    json={"decision": "override", "reviewer_role": "counsellor", "comment": "Flag was wrong."})
    assert r.status_code == 200 and r.json()["decision"] == "override"
    assert client.post(f"/api/reviews/{rev}/decision", json={"decision": "approve", "reviewer_role": "counsellor",
                                                             "comment": "again"}).status_code == 409
    audit = client.get("/api/audit", params={"run_id": run_id}).json()["entries"]
    kinds = {e["kind"] for e in audit}
    assert {"scenario_event", "agent", "coordinator", "human_decision"} <= kinds
    hd = [e for e in audit if e["kind"] == "human_decision"][0]
    assert hd["outcome"] == "override" and all((e["llm"] or {}).get("llm_calls", 0) == 0 for e in audit)
    hist = client.get(f"/api/scenarios/false_positive_controversy/runs/{run_id}").json()["events"]
    assert hist[-1]["type"] == "review_recorded"


def test_stream_replays_history(offline, instant, client):
    run_id, _, events = run_all(client, "false_positive_controversy")
    # Last-Event-ID close to the end: only the tail is replayed; read until the last envelope
    last = events[-1]["seq"]
    with client.stream("GET", f"/api/scenarios/false_positive_controversy/stream?run_id={run_id}",
                       headers={"Last-Event-ID": str(last - 2)}) as r:
        got = []
        for line in r.iter_lines():
            if line.startswith("data:"):
                got.append(json.loads(line[5:]))
            if got and got[-1]["seq"] == last:
                break
    assert [g["seq"] for g in got] == [last - 1, last]


def test_gaps_filters_and_radar(client):
    body = client.get("/api/gaps").json()
    assert len(body["gaps"]) == 6
    assert {g["gap_type"] for g in body["gaps"]} == {"legislative_gap", "missing_standard", "unclear_responsibility",
                                                     "coordination_problem", "objective_conflict"}
    radar = body["readiness_radar"]
    assert len(radar) == 8 and max(radar.values()) == 1.0 and sum(v > 0 for v in radar.values()) >= 6
    one = client.get("/api/gaps", params={"gap_type": "missing_standard"}).json()
    assert [g["id"] for g in one["gaps"]] == ["gap-edtech-ai-risk-standard"] and one["readiness_radar"] == radar
    for g in body["gaps"]:
        assert g["gap_analysis"].startswith("ANALYSIS (not law)")
        assert all(c["verified"] is False for c in g["uae_says"]["citations"])


def test_data_entries_listing(client):
    body = client.get("/api/data/entries").json()
    assert len(body["entries"]) == 8 and body["errors"] == []
    e = client.get("/api/data/entries/children-data-consent").json()
    assert e["citations"][0]["verified"] is False and e["file"] == "children_data.json"
    assert client.get("/api/data/entries/nope").status_code == 404


def test_audit_result_filter(offline, client):
    client.post("/api/ask", json={"question": "hello"})
    client.post("/api/ask", json={"question": "weather in Paris"})
    body = client.get("/api/audit", params={"outcome": "no_source"}).json()
    assert body["total"] == 1 and body["entries"][0]["mode"] == "no_source"


def test_guidance_has_clickable_examples_and_answers_have_details(offline, client):
    g = client.post("/api/ask", json={"question": "hello"}).json()
    assert len(g["suggested_topics"]) == 3 and g["pipeline_nodes"] == []
    a = client.post("/api/ask", json={"question": "Can an app show ads to minors?"}).json()
    assert "advertising-to-minors" in a["answer"]["details"]
