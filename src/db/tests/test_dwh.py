"""
Tests for src/db/dwh.py (SQLite DWH layer)
Run: python -m pytest src/db/tests -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
import src.db.dwh as dwh_mod


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets a fresh in-memory-like SQLite DB pointing at real CSVs."""
    db_path = tmp_path / "test_billing.db"
    monkeypatch.setattr(dwh_mod, "_DB_PATH", db_path)
    dwh_mod.reset_db()
    yield
    dwh_mod.reset_db()


# ── Schema & bootstrap ────────────────────────────────────────────────────────

def test_db_initialises():
    db = dwh_mod.get_db()
    assert db is not None


def test_tables_exist():
    db = dwh_mod.get_db()
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "billing_header"   in tables
    assert "billing_lines"    in tables
    assert "customer_context" in tables


def test_billing_header_row_count():
    dwh_mod.get_db()
    rows = dwh_mod._rows(dwh_mod.get_db().execute("SELECT COUNT(*) AS n FROM billing_header"))
    assert rows[0]["n"] >= 4


def test_billing_lines_row_count():
    dwh_mod.get_db()
    rows = dwh_mod._rows(dwh_mod.get_db().execute("SELECT COUNT(*) AS n FROM billing_lines"))
    assert rows[0]["n"] >= 12   # 3 lines × 4 bills


def test_customer_context_row_count():
    dwh_mod.get_db()
    rows = dwh_mod._rows(dwh_mod.get_db().execute("SELECT COUNT(*) AS n FROM customer_context"))
    assert rows[0]["n"] >= 2


# ── Query helpers ─────────────────────────────────────────────────────────────

def test_query_customer_by_account_found():
    row = dwh_mod.query_customer_by_account("123456789")
    assert row is not None
    assert row["customer_id"] == "cust-42"
    assert row["customer_name"] == "John Doe"


def test_query_customer_by_account_not_found():
    row = dwh_mod.query_customer_by_account("000000000")
    assert row is None


def test_query_customer_by_id():
    row = dwh_mod.query_customer_by_id("cust-99")
    assert row is not None
    assert row["customer_name"] == "Acme Energy SA"
    assert row["segment"] == "business"


def test_query_billing_history_returns_bills():
    bills = dwh_mod.query_billing_history("cust-42")
    assert len(bills) >= 2
    # Newest first
    assert bills[0]["issue_date"] >= bills[-1]["issue_date"]


def test_query_billing_history_limit():
    bills = dwh_mod.query_billing_history("cust-42", limit=2)
    assert len(bills) <= 2


def test_query_billing_lines():
    lines = dwh_mod.query_billing_lines("B-2026-0001")
    assert len(lines) == 3
    types = {l["charge_type"] for l in lines}
    assert types == {"energy", "regulated", "taxes"}


def test_query_avg_consumption():
    avg = dwh_mod.query_avg_consumption("cust-42")
    assert avg == 350.0


def test_query_last_n_bills_total():
    total = dwh_mod.query_last_n_bills_total("cust-42", n=3)
    # 152.34 + 120.00 + 110.50 = 382.84
    assert abs(total - 382.84) < 0.01


def test_query_unknown_customer_returns_defaults():
    assert dwh_mod.query_customer_by_id("cust-unknown") is None
    assert dwh_mod.query_billing_history("cust-nonexistent") == []
    assert dwh_mod.query_avg_consumption("cust-nonexistent") is None
    assert dwh_mod.query_last_n_bills_total("cust-nonexistent") == 0.0

