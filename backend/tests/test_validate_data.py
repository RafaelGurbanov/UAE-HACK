import json
import shutil
from pathlib import Path

from app.kb import validate_data
from app.kb.data_model import json_schema, load_data

DATA = Path(__file__).parents[2] / "kb" / "data"


def test_seed_data_is_valid_and_all_placeholders():
    r = load_data(DATA)
    assert r.errors == [] and len(r.entries) == 8
    for e in r.entries:
        assert e.citations and all(not c.verified and c.law == "SOURCE TO BE VERIFIED" and c.url == "" for c in e.citations)


def test_schema_file_matches_model():
    assert json.loads((DATA / "schema.json").read_text(encoding="utf-8")) == json_schema()


def test_validator_reports_duplicates_and_schema_errors(tmp_path, monkeypatch, capsys):
    d = tmp_path / "data"
    shutil.copytree(DATA, d)
    entries = json.loads((d / "education.json").read_text(encoding="utf-8"))
    (d / "dup.json").write_text(json.dumps(entries), encoding="utf-8")
    bad = dict(entries[0], id="bad-entry", pipeline_nodes=["XYZ"])
    del bad["answer"]
    (d / "bad.json").write_text(json.dumps([bad]), encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(d))
    from app.core.config import get_settings

    get_settings.cache_clear()
    assert validate_data.main([]) == 1
    out = capsys.readouterr().out
    assert "duplicate id 'counsellor-review'" in out
    assert "bad.json: entry 0 (id='bad-entry'), field answer: Field required" in out
    assert "field pipeline_nodes.0" in out
    assert "verified=false:" in out and "Result: FAILED" in out
