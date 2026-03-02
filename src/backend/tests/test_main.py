"""
Tests for src/backend/app/main.py
Run: python -m pytest src/backend/tests -v
"""
import sys, json, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
import pytest
from fastapi.testclient import TestClient
from src.backend.app.main import app
client = TestClient(app)
SAMPLE_EXTRACTED = {
    "extracted_id": "test-backend-001",
    "ocr_confidence": 0.95,
    "extraction_method": "rule_based",
    "bill_number": {"value": "B-2026-0001", "confidence": 0.99},
    "account_number": {"value": "123456789", "normalized": "123456789", "confidence": 0.98},
    "customer_name": {"value": "John Doe", "normalized": "john doe", "confidence": 0.95},
    "customer_address": ["1 Main St Athens"],
    "bill_date": {"value": "2026-01-15", "confidence": 0.98},
    "service_period": {"start": "2026-01-01", "end": "2026-01-31", "confidence": 0.97},
    "total_due": {"value": 152.34, "currency": "EUR", "confidence": 0.97},
    "line_items": [],
    "meter_ids": ["MTR-987"],
    "tariff_code": "T01",
    "match_hints": {"account_hash": "123456789", "name_norm": "john doe", "meter_list": ["MTR-987"]},
}
BILL_TEXT = (
    "Electricity Bill\nBill Date: 15/01/2026\nAccount No: 123456789\n"
    "Customer: John Doe\nAddress: 1 Main St, Athens\nTariff: T01\n"
    "Period From: 01/01/2026 To: 31/01/2026\nMeter: MTR-987\n\n"
    "Energy consumption  420 kWh  0.12  50.40\nRegulated charges  30.00\n"
    "Taxes  71.94\n\nTotal Due: EUR 152.34\n"
)
# ── Health ────────────────────────────────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["version"] == "0.2.0"
# ── Upload ────────────────────────────────────────────────────────────────────
def test_upload_returns_extracted(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    file_bytes = BILL_TEXT.encode()
    r = client.post(
        "/upload",
        files={"file": ("bill.txt", io.BytesIO(file_bytes), "text/plain")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "extracted_id" in body
    assert "agent" in body
    assert body["agent"] == "VisionAgent"
def test_upload_extracts_account(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post(
        "/upload",
        files={"file": ("bill.txt", io.BytesIO(BILL_TEXT.encode()), "text/plain")},
    )
    assert r.status_code == 200
    acct = r.json().get("account_number", {}).get("normalized")
    assert acct == "123456789"
def test_upload_persists_extracted(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post(
        "/upload",
        files={"file": ("bill.txt", io.BytesIO(BILL_TEXT.encode()), "text/plain")},
    )
    assert r.status_code == 200
    extracted_id = r.json()["extracted_id"]
    # Fetch it back
    r2 = client.get(f"/extracted/{extracted_id}")
    assert r2.status_code == 200
    assert r2.json()["extracted_id"] == extracted_id
# ── Extracted GET ─────────────────────────────────────────────────────────────
def test_extracted_not_found():
    r = client.get("/extracted/nonexistent-id-xyz")
    assert r.status_code == 404
# ── Match ─────────────────────────────────────────────────────────────────────
def test_match_exact():
    r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED})
    assert r.status_code == 200
    body = r.json()
    assert body["match_type"] == "exact"
    assert body["matched_customer_id"] == "cust-42"
def test_match_returns_agent_name():
    r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED})
    assert r.json()["agent"] == "MatcherAgent"
def test_match_none_for_unknown():
    unknown = {**SAMPLE_EXTRACTED,
               "account_number": {"value": "000000000", "normalized": "000000000"},
               "customer_name": {"value": "Zyx Qwerty Nobody", "normalized": "zyx qwerty nobody"},
               "customer_address": ["999 Nowhere Blvd"],
               "meter_ids": []}
    r = client.post("/match", json={"extracted": unknown})
    assert r.status_code == 200
    assert r.json()["match_type"] == "none"
def test_match_enriches_customer_context():
    r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED})
    body = r.json()
    assert body["customer_context"]["customer_name"] == "John Doe"
    assert len(body["billing_history"]) >= 1
# ── Explain ───────────────────────────────────────────────────────────────────
def test_explain_returns_answer(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    match_r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED}).json()
    payload = {
        "extracted": SAMPLE_EXTRACTED,
        "match_result": match_r,
        "question": "Why is my bill higher?",
    }
    r = client.post("/explain", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert len(body["answer"]) > 0
def test_explain_has_confidence(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    match_r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED}).json()
    r = client.post("/explain", json={
        "extracted": SAMPLE_EXTRACTED,
        "match_result": match_r,
        "question": "Explain my charges",
    })
    body = r.json()
    assert body["confidence_label"] in ("High", "Medium", "Low")
    assert 0.0 <= body["confidence_score"] <= 1.0
def test_explain_has_passages(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    match_r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED}).json()
    r = client.post("/explain", json={
        "extracted": SAMPLE_EXTRACTED,
        "match_result": match_r,
        "question": "What are regulated charges?",
    })
    assert len(r.json()["retrieved_passages"]) > 0
def test_explain_has_citations(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    match_r = client.post("/match", json={"extracted": SAMPLE_EXTRACTED}).json()
    r = client.post("/explain", json={
        "extracted": SAMPLE_EXTRACTED,
        "match_result": match_r,
        "question": "Q",
    })
    assert isinstance(r.json()["citations"], list)
# ── Pipeline ──────────────────────────────────────────────────────────────────
def test_pipeline_not_found():
    r = client.post("/pipeline", json={"extracted_id": "no-such-id", "question": "Q"})
    assert r.status_code == 404
def test_pipeline_end_to_end(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Upload first
    up = client.post(
        "/upload",
        files={"file": ("bill.txt", io.BytesIO(BILL_TEXT.encode()), "text/plain")},
    )
    extracted_id = up.json()["extracted_id"]
    # Then run pipeline
    r = client.post("/pipeline", json={"extracted_id": extracted_id, "question": "Why higher?"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "agent2_matcher" in body
    assert body["agent2_matcher"]["match_type"] == "exact"
