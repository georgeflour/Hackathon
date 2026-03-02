"""
Tests for src/rag/prompt_package.py and src/rag/llm_runner.py
Run: python -m pytest src/rag/tests -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.rag.prompt_package import build_prompt_package, SYSTEM_INSTRUCTIONS
from src.rag.llm_runner import run_llm, LlmAnswer, _confidence_from_passages

# ── Shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_EXTRACTED = {
    "extracted_id": "test-001",
    "bill_number":  {"value": "B-2026-0001", "confidence": 0.99},
    "account_number": {"value": "123456789", "normalized": "123456789", "confidence": 0.98},
    "customer_name":  {"value": "John Doe",  "normalized": "john doe",  "confidence": 0.95},
    "customer_address": ["1 Main St Athens"],
    "service_period":  {"start": "2026-01-01", "end": "2026-01-31"},
    "total_due":       {"value": 152.34, "currency": "EUR"},
    "line_items": [
        {"description": "energy consumption", "quantity_kwh": 420, "unit_price": 0.12, "amount": 50.40},
        {"description": "regulated charges",  "quantity_kwh": None,"unit_price": None, "amount": 30.00},
        {"description": "taxes",              "quantity_kwh": None,"unit_price": None, "amount": 71.94},
    ],
    "meter_ids":   ["MTR-987"],
    "tariff_code": "T01",
    "customer_context": {
        "customer_name": "John Doe",
        "segment": "residential",
        "active_tariff": "T01",
        "avg_kwh_6m": 350,
        "last_3_bills_total": 382.84,
    },
    "billing_history": [
        {"billing_id": "B-2026-0001", "period_from": "2026-01-01", "period_to": "2026-01-31", "total_amount": 152.34},
        {"billing_id": "B-2025-1201", "period_from": "2025-11-01", "period_to": "2025-11-30", "total_amount": 120.00},
    ],
}

SAMPLE_MATCH = {
    "match_type": "exact",
    "matched_customer_id": "cust-42",
    "score": 0.99,
    "candidates": [],
    "clarifying_question": None,
}

SAMPLE_PASSAGES = [
    {"passage_id": "faq-001-p1", "doc_id": "faq-001", "doc_title": "Why did my bill increase?",
     "page": 1, "text_snippet": "Your bill may increase due to higher consumption or tariff changes.", "final_score": 0.91},
    {"passage_id": "tariff-T01-p1", "doc_id": "tariff-T01", "doc_title": "Residential Tariff T01",
     "page": 1, "text_snippet": "Tariff T01: 0.12 EUR/kWh up to 500 kWh. Standing charge 5.00 EUR.", "final_score": 0.88},
    {"passage_id": "faq-002-p1", "doc_id": "faq-002", "doc_title": "Regulated charges",
     "page": 1, "text_snippet": "Regulated charges are set by the national regulator RAE.", "final_score": 0.85},
]


# ── prompt_package tests ──────────────────────────────────────────────────────

def test_build_prompt_package_returns_dict():
    pkg = build_prompt_package("Why is my bill higher?", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    assert isinstance(pkg, dict)


def test_package_has_all_required_keys():
    pkg = build_prompt_package("Why is my bill higher?", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    required = {
        "package_id", "created_at", "system_instructions", "user_question",
        "extracted_bill_summary", "matched_customer", "retrieval_queries",
        "retrieved_passages", "citation_policy", "hallucination_policy",
        "generation_parameters",
    }
    assert required.issubset(pkg.keys())


def test_package_id_is_unique():
    pkg1 = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    pkg2 = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    assert pkg1["package_id"] != pkg2["package_id"]


def test_package_id_has_pkg_prefix():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    assert pkg["package_id"].startswith("pkg-")


def test_system_instructions_contains_grounding_rules():
    assert "ONLY" in SYSTEM_INSTRUCTIONS
    assert "citation" in SYSTEM_INSTRUCTIONS.lower()
    assert "hallucinate" in SYSTEM_INSTRUCTIONS.lower() or "speculate" in SYSTEM_INSTRUCTIONS.lower()


def test_system_instructions_in_package():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    assert pkg["system_instructions"] == SYSTEM_INSTRUCTIONS


def test_temperature_is_zero():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    assert pkg["generation_parameters"]["temperature"] == 0.0


def test_citation_policy_present():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    cp = pkg["citation_policy"]
    assert cp["require_citation_for_numeric_claims"] is True
    assert "{doc_id}" in cp["format"]


def test_retrieval_queries_built():
    pkg = build_prompt_package("Why is my bill higher?", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    queries = pkg["retrieval_queries"]
    assert len(queries) == 2
    types = {q["type"] for q in queries}
    assert "metadata" in types and "semantic" in types


def test_extracted_bill_summary_populated():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    s = pkg["extracted_bill_summary"]
    assert s["account_number"] == "123456789"
    assert s["total_due"]["value"] == 152.34
    assert s["tariff_code"] == "T01"


def test_passages_forwarded():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    assert len(pkg["retrieved_passages"]) == len(SAMPLE_PASSAGES)


def test_created_at_is_timezone_aware():
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, [])
    assert "+00:00" in pkg["created_at"] or "Z" in pkg["created_at"] or "00:00" in pkg["created_at"]


# ── llm_runner tests ──────────────────────────────────────────────────────────

def test_llm_runner_stub_returns_llm_answer(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pkg = build_prompt_package("Why is my bill higher?", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    result = run_llm(pkg)
    assert isinstance(result, LlmAnswer)


def test_llm_runner_stub_answer_non_empty(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pkg = build_prompt_package("Why is my bill higher?", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    result = run_llm(pkg)
    assert len(result.answer_text) > 50


def test_llm_runner_stub_has_citations(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    result = run_llm(pkg)
    assert isinstance(result.citations, list)
    assert len(result.citations) > 0


def test_llm_runner_stub_confidence_label(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pkg = build_prompt_package("Q", SAMPLE_EXTRACTED, SAMPLE_MATCH, SAMPLE_PASSAGES)
    result = run_llm(pkg)
    assert result.confidence_label in ("High", "Medium", "Low")


def test_confidence_low_with_no_passages():
    score, label = _confidence_from_passages([])
    assert score == 0.4
    assert label == "Low"


def test_confidence_high_with_good_scores():
    passages = [{"final_score": 0.95}, {"final_score": 0.92}, {"final_score": 0.90}]
    score, label = _confidence_from_passages(passages)
    assert label == "High"
    assert score >= 0.85


def test_confidence_medium():
    passages = [{"final_score": 0.70}, {"final_score": 0.68}]
    score, label = _confidence_from_passages(passages)
    assert label == "Medium"


def test_confidence_low_with_poor_scores():
    passages = [{"final_score": 0.30}, {"final_score": 0.25}]
    score, label = _confidence_from_passages(passages)
    assert label == "Low"

