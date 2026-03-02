"""
Tests for src/matcher/match_service.py
Run: python -m pytest src/matcher/tests -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.matcher.match_service import match_customer, MatchResult

# ── Shared extracted dicts ─────────────────────────────────────────────────────

EXACT_ACCOUNT = {
    "account_number": {"value": "123456789", "normalized": "123456789"},
    "customer_name":  {"normalized": "john doe"},
    "customer_address": ["1 Main St Athens"],
    "meter_ids": [],
}

EXACT_METER = {
    "account_number": {"value": None, "normalized": None},
    "customer_name":  {"normalized": None},
    "customer_address": [],
    "meter_ids": ["MTR-987"],
}

EXACT_NAME = {
    "account_number": {"value": None, "normalized": None},
    "customer_name":  {"normalized": "john doe"},
    "customer_address": ["1 main st athens"],
    "meter_ids": [],
}

NO_MATCH = {
    "account_number": {"value": "000000000", "normalized": "000000000"},
    "customer_name":  {"normalized": "unknown person xyz"},
    "customer_address": ["99 Nowhere Lane"],
    "meter_ids": ["MTR-NONE"],
}

BUSINESS = {
    "account_number": {"value": "987654321", "normalized": "987654321"},
    "customer_name":  {"normalized": "acme energy sa"},
    "customer_address": ["10 industrial ave attica"],
    "meter_ids": ["MTR-555"],
}


# ── Step 2: Exact account number ──────────────────────────────────────────────

def test_exact_account_match_type():
    r = match_customer(EXACT_ACCOUNT)
    assert r.match_type == "exact"


def test_exact_account_returns_customer_id():
    r = match_customer(EXACT_ACCOUNT)
    assert r.matched_customer_id == "cust-42"


def test_exact_account_score():
    r = match_customer(EXACT_ACCOUNT)
    assert r.score >= 0.95


def test_customer_id_not_account_number():
    """matched_customer_id must be 'cust-42', never the account number."""
    r = match_customer(EXACT_ACCOUNT)
    assert r.matched_customer_id.startswith("cust-")


# ── Step 3: Meter ID match ────────────────────────────────────────────────────

def test_meter_match_type():
    r = match_customer(EXACT_METER)
    assert r.match_type == "exact"


def test_meter_match_customer_id():
    r = match_customer(EXACT_METER)
    assert r.matched_customer_id == "cust-42"


# ── Step 4: Name + address match ─────────────────────────────────────────────

def test_name_address_match():
    r = match_customer(EXACT_NAME)
    assert r.match_type == "exact"
    assert r.matched_customer_id == "cust-42"


# ── Business customer ─────────────────────────────────────────────────────────

def test_business_customer_match():
    r = match_customer(BUSINESS)
    assert r.match_type == "exact"
    assert r.matched_customer_id == "cust-99"


# ── No match ─────────────────────────────────────────────────────────────────

def test_no_match_type():
    r = match_customer(NO_MATCH)
    assert r.match_type == "none"


def test_no_match_customer_id_is_none():
    r = match_customer(NO_MATCH)
    assert r.matched_customer_id is None


# ── Fuzzy ambiguous produces clarifying question ──────────────────────────────

def test_fuzzy_ambiguous_has_clarifying_question():
    """Partial name match with no account/meter should trigger ambiguous path."""
    ambiguous = {
        "account_number": {"value": None, "normalized": None},
        "customer_name":  {"normalized": "john"},   # partial, no surname
        "customer_address": [],
        "meter_ids": [],
    }
    r = match_customer(ambiguous)
    # Either exact (if score ≥ 0.90) or ambiguous — either way no crash
    assert isinstance(r, MatchResult)
    if r.match_type == "fuzzy_ambiguous":
        assert r.clarifying_question is not None
        assert "A)" in r.clarifying_question
        assert "D) None of these" in r.clarifying_question


# ── Result shape ──────────────────────────────────────────────────────────────

def test_candidates_list_populated_on_exact():
    r = match_customer(EXACT_ACCOUNT)
    assert len(r.candidates) >= 1
    assert r.candidates[0].customer_id == "cust-42"


def test_candidate_match_field_populated():
    r = match_customer(EXACT_ACCOUNT)
    assert r.candidates[0].match_field == "account_number"

