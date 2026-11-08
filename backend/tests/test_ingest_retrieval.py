import json

from app.kb.chunking import chunk_document, split_articles
from app.kb.index import get_index
from app.kb.registry import read_rows
from app.kb.retrieval import retrieve
from app.kb.text import detect_language, normalize_for_match


def test_article_splitting_english_and_arabic():
    en = "Preamble text\nArticle 1 Scope\nThis applies.\nArticle 2\nSecond rule here.\nArticle 1 of this Law is cited here."
    segs = split_articles(en)
    assert [s.article for s in segs] == [None, "1", "2"]  # in-text back-reference does not restart numbering
    ar = "ديباجة\nالمادة (1)\nنص المادة الأولى.\nالمادة (٢)\nنص المادة الثانية هنا."
    assert [s.article for s in split_articles(ar)] == [None, "1", "2"]


def test_long_article_is_split_but_keeps_number():
    text = "Article 1\n" + ("This is a long sentence about personal data. " * 120) + "\nArticle 2\nShort."
    chunks, n = chunk_document(text)
    parts = [c for c in chunks if c["article"] == "1"]
    assert n == 2 and len(parts) > 1 and all(len(c["text"]) <= 2000 for c in parts)


def test_language_and_normalisation():
    assert detect_language("ما الموافقة المطلوبة؟") == "ar" and detect_language("What consent?") == "en"
    assert normalize_for_match("«المادةُ»  ٥") == normalize_for_match("المادة 5")


def test_ingest_auto_registers_and_indexes(kb_with_doc):
    rows = read_rows(kb_with_doc)
    assert rows[0]["doc_id"] == "demo-act" and rows[0]["verified"] == "false"
    assert "SOURCE TO BE VERIFIED" in rows[0]["notes"]
    lines = (kb_with_doc / "processed" / "demo-act.jsonl").read_text(encoding="utf-8").splitlines()
    arts = [json.loads(x)["article"] for x in lines]
    assert arts[:6] == [None, "1", "2", "3", "4", "5"]
    idx = get_index()
    assert idx.dense_count() == len(lines) == len(idx.chunks)


def test_ingest_skips_unchanged_files(kb_with_doc, capsys):
    from app.kb import ingest

    assert ingest.main([]) == 0
    assert "skipped (unchanged)" in capsys.readouterr().out


def test_hybrid_retrieval_finds_the_right_article(kb_with_doc):
    r = retrieve(get_index(), "Can a controller use a child's data for targeted advertising?", [], ["uae_federal"])
    assert r.hits[0].chunk["article"] == "3"
    assert r.score_kind == "dense" and r.supported
    r2 = retrieve(get_index(), "What does Article 4 say?", [], ["uae_federal"])
    assert r2.hits[0].chunk["article"] == "4"


def test_layer_filter_excludes_everything(kb_with_doc):
    r = retrieve(get_index(), "consent of a child", [], ["global_example"])
    assert r.hits == [] and not r.supported
