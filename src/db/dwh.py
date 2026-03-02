"""
db/dwh.py
---------
SQLite-backed DWH layer.

On first call to `get_db()` the three DWH CSVs are imported into an
in-process SQLite database (data/dwh/billing.db).  Subsequent calls
reuse the same connection via a module-level singleton.

Tables
------
  billing_header   — one row per bill
  billing_lines    — line items per bill
  customer_context — customer profile + consumption history

Why SQLite instead of raw CSV?
  • Exact lookups (account, customer_id) are O(1) with an index vs O(n) scan
  • JOINs: get a customer's billing history in one query
  • Aggregations: avg kWh, sum of last-N bills
  • Zero-config, file-based — no server to run
  • Same SQL queries work on Postgres in production (swap connection string)

Usage
-----
    from src.db.dwh import get_db, query_customer_by_account, query_billing_history

    db = get_db()   # initialises on first call, reuses after
    row = query_customer_by_account("123456789")
    bills = query_billing_history("cust-42", limit=3)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

# ─── paths ────────────────────────────────────────────────────────────────────
_ROOT        = Path(__file__).parent.parent.parent
_DWH_DIR     = _ROOT / "data" / "dwh"
_DB_PATH     = _DWH_DIR / "billing.db"
_HEADER_CSV  = _DWH_DIR / "Billing_Header.csv"
_LINES_CSV   = _DWH_DIR / "Billing_Lines.csv"
_CONTEXT_CSV = _DWH_DIR / "Customer_Context.csv"

# Module-level connection singleton
_conn: sqlite3.Connection | None = None


# ─── schema ───────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS billing_header (
    billing_id   TEXT PRIMARY KEY,
    issue_date   TEXT,
    period_from  TEXT,
    period_to    TEXT,
    customer_id  TEXT,
    contract_id  TEXT,
    account_id   TEXT,
    supply_number TEXT,
    tariff_code  TEXT,
    total_amount REAL,
    currency     TEXT
);

CREATE TABLE IF NOT EXISTS billing_lines (
    line_id      TEXT PRIMARY KEY,
    billing_id   TEXT,
    charge_type  TEXT,
    description  TEXT,
    quantity_kwh REAL,
    unit_price   REAL,
    amount       REAL,
    unit         TEXT,
    FOREIGN KEY (billing_id) REFERENCES billing_header(billing_id)
);

CREATE TABLE IF NOT EXISTS customer_context (
    customer_id         TEXT PRIMARY KEY,
    account_numbers     TEXT,
    primary_account     TEXT,
    customer_name       TEXT,
    addresses           TEXT,
    service_meters      TEXT,
    active_tariff       TEXT,
    segment             TEXT,
    region              TEXT,
    avg_kwh_6m          REAL,
    last_3_bills_total  REAL
);

CREATE INDEX IF NOT EXISTS idx_header_customer   ON billing_header(customer_id);
CREATE INDEX IF NOT EXISTS idx_header_account    ON billing_header(account_id);
CREATE INDEX IF NOT EXISTS idx_lines_billing     ON billing_lines(billing_id);
CREATE INDEX IF NOT EXISTS idx_ctx_account       ON customer_context(primary_account);
"""


# ─── bootstrap ────────────────────────────────────────────────────────────────

def _import_csvs(conn: sqlite3.Connection) -> None:
    """Load the three CSVs into SQLite (idempotent via INSERT OR IGNORE)."""
    for csv_path, table in [
        (_HEADER_CSV,  "billing_header"),
        (_LINES_CSV,   "billing_lines"),
        (_CONTEXT_CSV, "customer_context"),
    ]:
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, dtype=str)
        # Convert numeric columns
        for col in ("total_amount", "avg_kwh_6m", "last_3_bills_total",
                    "quantity_kwh", "unit_price", "amount"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df.to_sql(table, conn, if_exists="replace", index=False)
    conn.commit()


def get_db(db_path: Path = _DB_PATH) -> sqlite3.Connection:
    """
    Return a singleton SQLite connection, initialising the schema and
    importing CSVs on the first call.
    """
    global _conn
    if _conn is not None:
        return _conn
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    _import_csvs(conn)
    _conn = conn
    return _conn


def reset_db() -> None:
    """Force a fresh connection (useful in tests with tmp databases)."""
    global _conn
    if _conn:
        _conn.close()
    _conn = None


# ─── query helpers ────────────────────────────────────────────────────────────

def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def query_customer_by_account(account_id: str) -> dict[str, Any] | None:
    """Look up a customer by exact account number. Returns None if not found."""
    conn = get_db()
    rows = _rows(conn.execute(
        "SELECT * FROM customer_context "
        "WHERE primary_account = ? OR account_numbers = ?",
        (account_id, account_id),
    ))
    return rows[0] if rows else None


def query_customer_by_id(customer_id: str) -> dict[str, Any] | None:
    """Look up a customer by customer_id. Returns None if not found."""
    conn = get_db()
    rows = _rows(conn.execute(
        "SELECT * FROM customer_context WHERE customer_id = ?",
        (customer_id,),
    ))
    return rows[0] if rows else None


def query_billing_history(
    customer_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return billing headers for a customer, newest first."""
    conn = get_db()
    return _rows(conn.execute(
        "SELECT * FROM billing_header "
        "WHERE customer_id = ? "
        "ORDER BY issue_date DESC LIMIT ?",
        (customer_id, limit),
    ))


def query_billing_lines(billing_id: str) -> list[dict[str, Any]]:
    """Return all line items for a given bill."""
    conn = get_db()
    return _rows(conn.execute(
        "SELECT * FROM billing_lines WHERE billing_id = ?",
        (billing_id,),
    ))


def query_avg_consumption(customer_id: str) -> float | None:
    """Return avg_kwh_6m for a customer from customer_context."""
    conn = get_db()
    rows = _rows(conn.execute(
        "SELECT avg_kwh_6m FROM customer_context WHERE customer_id = ?",
        (customer_id,),
    ))
    return rows[0]["avg_kwh_6m"] if rows else None


def query_last_n_bills_total(customer_id: str, n: int = 3) -> float:
    """Sum of the last N bills for a customer."""
    conn = get_db()
    rows = _rows(conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total "
        "FROM ("
        "  SELECT total_amount FROM billing_header "
        "  WHERE customer_id = ? "
        "  ORDER BY issue_date DESC LIMIT ?"
        ")",
        (customer_id, n),
    ))
    return float(rows[0]["total"]) if rows else 0.0

