"""
Tests for all three agents + orchestrator.
Run: python -m pytest src/agents/tests -v
"""
import sys
from dataclasses import asdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest

from src.agents.vision_agent  import run_vision_agent
from src.agents.matcher_agent import run_matcher_agent
from src.agents.reply_agent   import run_reply_agent
from src.agents.orchestrator  import run_pipeline


# ── Shared sample extracted bill (account 123456789 = cust-42) ────────────────

SAMPLE_EXTRACTED = {
    "extracted_id":   "test-001",
    "ocr_confidence": 0.95,
    "bill_number":    {"value": "B-2026-0001", "confidence": 0.99},
    "account_number": {"value": "123456789", "normalized": "123456789", "confidence": 0.98},
    "customer_name":  {"value": "John Doe",  "normalized": "john doe",  "confidence": 0.95},
    "customer_address": ["1 Main St Athens"],
    "bill_date":        {"value": "2026-01-15", "confidence": 0.98},
    "service_period":   {"start": "2026-01-01", "end": "2026-01-31", "confidence": 0.97},
    "total_due":        {"value": 152.34, "currency": "EUR", "confidence": 0.97},
    "line_items": [
        {"description": "energy consumption", "quantity_kwh": 420, "unit_price": 0.12, "amount": 50.40},
        {"description": "regulated charges",  "quantity_kwh": None, "unit_price": None, "amount": 30.00},
        {"description": "taxes",              "quantity_kwh": None, "unit_price": None, "amount": 71.94},
    ],
    "meter_ids":   ["MTR-987"],
    "tariff_code": "T01",
    "match_hints": {"account_hash": "123456789", "name_norm": "john doe", "meter_list": ["MTR-987"]},
}

# Bill text used by VisionAgent rule-based fallback tests
BILL_TEXT = (
    "Electricity Bill\n"
    "Bill Date: 15/01/2026\n"
    "Account No: 123456789\n"
    "Customer: John Doe\n"
    "Address: 1 Main St, Athens\n"
    "Tariff: T01\n"
    "Period From: 01/01/2026 To: 31/01/2026\n"
    "Meter: MTR-987\n\n"
    "Energy consumption  420 kWh  0.12  50.40\n"
    "Regulated charges  30.00\n"
    "Taxes  71.94\n\n"
    "Total Due: EUR 152.34\n"
)


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 1 — VisionAgent
# ═══════════════════════════════════════════════════════════════════════════════

def test_vision_agent_name():
    # Create a temp text file to trigger rule-based fallback
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(BILL_TEXT)
        tmp = f.name
    try:
        result = run_vision_agent(tmp)
        assert result.agent_name == "VisionAgent"
    finally:
        os.unlink(tmp)


def test_vision_agent_rule_based_extracts_account(tmp_path):
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_vision_agent(bill)
    assert result.extracted["account_number"]["normalized"] == "123456789"


def test_vision_agent_rule_based_extracts_total(tmp_path):
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_vision_agent(bill)
    assert result.extracted["total_due"]["value"] == 152.34


def test_vision_agent_extraction_method(tmp_path):
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_vision_agent(bill)
    assert result.extraction_method == "rule_based"


def test_vision_agent_returns_ocr_confidence(tmp_path):
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_vision_agent(bill)
    assert 0.0 <= result.ocr_confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 2 — MatcherAgent
# ═══════════════════════════════════════════════════════════════════════════════

def test_matcher_agent_name():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert result.agent_name == "MatcherAgent"


def test_matcher_agent_exact_match():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert result.match_type == "exact"
    assert result.matched_customer_id == "cust-42"


def test_matcher_agent_score():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert result.score >= 0.95


def test_matcher_agent_customer_id_format():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert result.matched_customer_id.startswith("cust-")


def test_matcher_agent_enriches_customer_context():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert result.customer_context != {}
    assert result.customer_context.get("customer_name") == "John Doe"
    assert result.customer_context.get("segment") == "residential"


def test_matcher_agent_enriches_billing_history():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    assert isinstance(result.billing_history, list)
    assert len(result.billing_history) >= 2
    # Newest bill first (sorted by issue_date DESC)
    assert result.billing_history[0]["billing_id"] == "B-2026-0001"


def test_matcher_agent_billing_history_has_line_items():
    result = run_matcher_agent(SAMPLE_EXTRACTED)
    first_bill = result.billing_history[0]
    assert "line_items" in first_bill
    assert len(first_bill["line_items"]) == 3


def test_matcher_agent_no_match():
    no_match = {
        **SAMPLE_EXTRACTED,
        "account_number": {"value": "000000000", "normalized": "000000000"},
        "meter_ids": [],
        "customer_name": {"normalized": "nobody xyz"},
    }
    result = run_matcher_agent(no_match)
    assert result.match_type == "none"
    assert result.matched_customer_id is None
    assert result.customer_context == {}
    assert result.billing_history == []


def test_matcher_agent_business_customer():
    biz = {
        **SAMPLE_EXTRACTED,
        "account_number": {"value": "987654321", "normalized": "987654321"},
        "meter_ids": ["MTR-555"],
    }
    result = run_matcher_agent(biz)
    assert result.matched_customer_id == "cust-99"
    assert result.customer_context.get("segment") == "business"


# ═══════════════════════════════════════════════════════════════════════════════
# Agent 3 — ReplyAgent
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def matcher_dict():
    return asdict(run_matcher_agent(SAMPLE_EXTRACTED))


def test_reply_agent_name(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Why is my bill higher?", SAMPLE_EXTRACTED, matcher_dict)
    assert result.agent_name == "ReplyAgent"


def test_reply_agent_returns_answer(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Why is my bill higher?", SAMPLE_EXTRACTED, matcher_dict)
    assert isinstance(result.answer_text, str)
    assert len(result.answer_text) > 50


def test_reply_agent_retrieves_passages(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("What are regulated charges?", SAMPLE_EXTRACTED, matcher_dict)
    assert len(result.retrieved_passages) > 0


def test_reply_agent_passages_have_correct_shape(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Explain my bill", SAMPLE_EXTRACTED, matcher_dict)
    for p in result.retrieved_passages:
        assert "passage_id"   in p
        assert "doc_id"       in p
        assert "text_snippet" in p
        assert "final_score"  in p


def test_reply_agent_max_6_passages(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Tell me everything about my bill", SAMPLE_EXTRACTED, matcher_dict)
    assert len(result.retrieved_passages) <= 6


def test_reply_agent_confidence_label(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Why is my bill higher?", SAMPLE_EXTRACTED, matcher_dict)
    assert result.confidence_label in ("High", "Medium", "Low")


def test_reply_agent_confidence_score_range(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Why is my bill higher?", SAMPLE_EXTRACTED, matcher_dict)
    assert 0.0 <= result.confidence_score <= 1.0


def test_reply_agent_has_prompt_package_id(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Q", SAMPLE_EXTRACTED, matcher_dict)
    assert result.prompt_package_id.startswith("pkg-")


def test_reply_agent_citations_list(matcher_dict, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_reply_agent("Q", SAMPLE_EXTRACTED, matcher_dict)
    assert isinstance(result.citations, list)


# ═══════════════════════════════════════════════════════════════════════════════
# Orchestrator — end-to-end
# ═══════════════════════════════════════════════════════════════════════════════

def test_orchestrator_returns_answer(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_pipeline(image_path=bill, question="Why is my bill higher?")
    assert "answer" in result
    assert len(result["answer"]) > 0


def test_orchestrator_has_all_agent_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_pipeline(image_path=bill, question="Explain my charges")
    assert "agent1_vision"  in result
    assert "agent2_matcher" in result
    assert "agent3_reply"   in result


def test_orchestrator_exact_match(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_pipeline(image_path=bill, question="Q")
    assert result["agent2_matcher"]["match_type"] == "exact"
    assert result["agent2_matcher"]["matched_customer_id"] == "cust-42"


def test_orchestrator_confidence_present(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    bill = tmp_path / "bill.txt"
    bill.write_text(BILL_TEXT)
    result = run_pipeline(image_path=bill, question="Q")
    assert result["confidence_label"] in ("High", "Medium", "Low")
    assert 0.0 <= result["confidence_score"] <= 1.0

