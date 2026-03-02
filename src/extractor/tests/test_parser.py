"""
Tests for src/extractor/parser.py
Run: python -m pytest src/extractor/tests -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.extractor.parser import extract_fields

# ── Shared sample bill text ────────────────────────────────────────────────────
SAMPLE = """
Electricity Bill
Bill Date: 15/01/2026
Account No: 123456789
Customer: John Doe
Address: 1 Main St, Athens
Tariff: T01
Period From: 01/01/2026 To: 31/01/2026
Meter: MTR-987

Energy consumption  420 kWh  0.12  50.40
Regulated charges  30.00
Taxes  71.94

Total Due: EUR 152.34
"""


def test_extract_account_number():
    r = extract_fields(SAMPLE)
    assert r["account_number"]["normalized"] == "123456789"
    assert r["account_number"]["value"] == "123456789"


def test_extract_total_due():
    r = extract_fields(SAMPLE)
    assert r["total_due"]["value"] == 152.34
    assert r["total_due"]["currency"] == "EUR"


def test_extract_meter_ids():
    r = extract_fields(SAMPLE)
    assert "MTR-987" in r["meter_ids"]


def test_extract_line_items():
    r = extract_fields(SAMPLE)
    items = r["line_items"]
    assert len(items) >= 1
    energy = next((i for i in items if "energy" in i["description"]), None)
    assert energy is not None, "Energy line item not found"
    assert energy["quantity_kwh"] == 420.0
    assert energy["unit_price"] == 0.12
    assert energy["amount"] == 50.40


def test_extract_service_period():
    r = extract_fields(SAMPLE)
    sp = r["service_period"]
    assert sp["start"] is not None
    assert sp["end"] is not None


def test_extract_customer_name():
    r = extract_fields(SAMPLE)
    assert r["customer_name"]["normalized"] is not None
    assert "john doe" in r["customer_name"]["normalized"]


def test_extract_tariff_code():
    r = extract_fields(SAMPLE)
    assert r["tariff_code"] == "T01"


def test_extract_bill_date():
    r = extract_fields(SAMPLE)
    assert r["bill_date"]["value"] is not None
    assert "2026" in r["bill_date"]["value"]


def test_confidence_scores_populated():
    r = extract_fields(SAMPLE)
    assert r["account_number"]["confidence"] > 0
    assert r["total_due"]["confidence"] > 0
    assert r["customer_name"]["confidence"] > 0


def test_match_hints_populated():
    r = extract_fields(SAMPLE)
    assert r["match_hints"]["account_hash"] == "123456789"
    assert r["match_hints"]["name_norm"] is not None
    assert "MTR-987" in r["match_hints"]["meter_list"]


def test_ocr_confidence_passed_through():
    r = extract_fields(SAMPLE, ocr_confidence=0.87)
    assert r["ocr_confidence"] == 0.87


def test_empty_text_returns_nulls():
    r = extract_fields("")
    assert r["account_number"]["value"] is None
    assert r["total_due"]["value"] is None
    assert r["meter_ids"] == []


def test_total_due_currency_before_amount():
    """Handle 'EUR 152.34' format (currency code before number)."""
    text = "Total Due: EUR 152.34"
    r = extract_fields(text)
    assert r["total_due"]["value"] == 152.34


def test_total_due_euro_symbol():
    """Handle '€152.34' format."""
    text = "Total Due: €152.34"
    r = extract_fields(text)
    assert r["total_due"]["value"] == 152.34

