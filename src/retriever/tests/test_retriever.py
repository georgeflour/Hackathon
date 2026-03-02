"""
Tests for src/retriever/retriever.py
Run: python -m pytest src/retriever/tests -v
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_knowledge(tmp_path, monkeypatch):
    """
    Write 3 minimal knowledge docs to a temp dir and redirect the retriever
    to use that directory (and a temp index location).
    """
    docs = [
        {"doc_id": "faq-001", "title": "Why did my bill increase?",  "page": 1,
         "text": "Your electricity bill may increase due to higher energy consumption, tariff rate adjustments, regulated charges such as network fees and levies, or an estimated bill catch-up."},
        {"doc_id": "faq-002", "title": "What are regulated charges?", "page": 1,
         "text": "Regulated charges are mandatory fees set by the national energy regulator. They include network use-of-system charges, renewable energy levy ETMEAR, capacity mechanism charge, and PSO levy."},
        {"doc_id": "tariff-T01", "title": "Residential Tariff T01",   "page": 1,
         "text": "Tariff T01 is the standard residential tariff. Energy charge 0.12 EUR per kWh up to 500 kWh per month. Standing charge 5.00 EUR per month. VAT 13 percent."},
    ]
    for d in docs:
        (tmp_path / f"{d['doc_id']}.json").write_text(json.dumps(d))

    import src.retriever.retriever as mod
    monkeypatch.setattr(mod, "_KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_INDEX_PATH",    tmp_path / "index.faiss")
    monkeypatch.setattr(mod, "_META_PATH",     tmp_path / "index_meta.json")
    # Reset singletons so the fixture's directory is picked up
    mod._index = None
    mod._meta  = []
    mod._model = None
    yield tmp_path
    # Cleanup singletons after test
    mod._index = None
    mod._meta  = []
    mod._model = None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_retrieve_returns_list(tmp_knowledge):
    from src.retriever.retriever import retrieve
    result = retrieve("electricity bill charges", top_k=3)
    assert isinstance(result, list)


def test_retrieve_non_empty_for_relevant_query(tmp_knowledge):
    from src.retriever.retriever import retrieve
    result = retrieve("regulated charges network fees", top_k=3)
    assert len(result) > 0


def test_retrieve_top_k_respected(tmp_knowledge):
    from src.retriever.retriever import retrieve
    result = retrieve("electricity consumption tariff", top_k=2)
    assert len(result) <= 2


def test_retrieve_empty_corpus(tmp_path, monkeypatch):
    import src.retriever.retriever as mod
    monkeypatch.setattr(mod, "_KNOWLEDGE_DIR", tmp_path)
    monkeypatch.setattr(mod, "_INDEX_PATH",    tmp_path / "index.faiss")
    monkeypatch.setattr(mod, "_META_PATH",     tmp_path / "index_meta.json")
    mod._index = None
    mod._meta  = []
    mod._model = None
    from src.retriever.retriever import retrieve
    result = retrieve("anything", top_k=5)
    assert result == []
    mod._index = None
    mod._meta  = []
    mod._model = None


def test_passage_shape(tmp_knowledge):
    from src.retriever.retriever import retrieve
    results = retrieve("bill increase consumption", top_k=3)
    assert len(results) > 0
    for r in results:
        assert "passage_id" in r
        assert "doc_id"     in r
        assert "text_snippet" in r
        assert "final_score"  in r
        assert 0.0 <= r["final_score"] <= 1.0


def test_passage_id_format(tmp_knowledge):
    from src.retriever.retriever import retrieve
    results = retrieve("tariff residential", top_k=2)
    for r in results:
        # format: "{doc_id}-p{page}"
        assert "-p" in r["passage_id"]


def test_retrieve_finds_tariff_doc(tmp_knowledge):
    from src.retriever.retriever import retrieve
    results = retrieve("tariff T01 residential kWh rate", top_k=3)
    doc_ids = [r["doc_id"] for r in results]
    assert "tariff-T01" in doc_ids


def test_bm25_fallback(tmp_knowledge, monkeypatch):
    """Force BM25 backend and ensure results are still returned."""
    import src.retriever.retriever as mod
    monkeypatch.setattr(mod, "_BACKEND", "bm25")
    mod._index = None
    results = mod.retrieve("regulated charges network fees levy", top_k=3)
    assert isinstance(results, list)
    assert len(results) > 0
    monkeypatch.setattr(mod, "_BACKEND", "vector")
    mod._index = None

