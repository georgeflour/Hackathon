"""
data/dwh/init_billing_db.py
---------------------------
Creates and seeds the local SQLite billing_structured.db with the exact
schema from sql.txt (Billing_Header, Billing_Lines, Customer_Context).

Run once:
    python data/dwh/init_billing_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "billing_structured.db"


DDL = """
CREATE TABLE IF NOT EXISTS Billing_Header (
    bill_id       INTEGER PRIMARY KEY AUTOINCREMENT,

    issue_date    TEXT    NOT NULL,
    period_from   TEXT    NOT NULL,
    period_to     TEXT    NOT NULL,

    customer_id   INTEGER NOT NULL,
    contract_id   INTEGER NOT NULL,
    account_id    TEXT    NOT NULL,

    supply_number INTEGER,
    meter_id      TEXT,

    tariff_code   TEXT    NOT NULL,

    total_amount  REAL    NOT NULL,

    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Billing_Lines (
    line_id       INTEGER PRIMARY KEY AUTOINCREMENT,

    bill_id       INTEGER NOT NULL,

    charge_type   TEXT    NOT NULL,
    -- 'energy' / 'regulated' / 'taxes' / 'other'

    description   TEXT,

    quantity_kwh  REAL,
    unit_price    REAL,
    amount        REAL    NOT NULL,

    CONSTRAINT FK_BillingLines_Bill
        FOREIGN KEY (bill_id)
        REFERENCES Billing_Header(bill_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Customer_Context (
    customer_id        INTEGER NOT NULL,
    contract_id        INTEGER NOT NULL,
    account_id         TEXT    NOT NULL,

    active_tariff      TEXT    NOT NULL,
    segment            TEXT    NOT NULL,
    -- 'residential' / 'business'

    region             TEXT,

    avg_kwh_6m         REAL,
    last_3_bills_total REAL,

    PRIMARY KEY (customer_id, contract_id)
);

CREATE INDEX IF NOT EXISTS idx_bh_customer  ON Billing_Header(customer_id);
CREATE INDEX IF NOT EXISTS idx_bh_account   ON Billing_Header(account_id);
CREATE INDEX IF NOT EXISTS idx_bl_bill      ON Billing_Lines(bill_id);
CREATE INDEX IF NOT EXISTS idx_cc_account   ON Customer_Context(account_id);
"""

SEED_SQL = """
INSERT INTO Billing_Header (
    issue_date, period_from, period_to,
    customer_id, contract_id, account_id,
    supply_number, meter_id, tariff_code, total_amount
) VALUES (
    '2026-02-06', '2025-12-31', '2026-02-04',
    1, 1, '1476458196',
    100295749, NULL, 'Γ1Ν', 182.00
);

INSERT INTO Billing_Lines (bill_id, charge_type, description, quantity_kwh, unit_price, amount) VALUES
    (1, 'energy',    'Energy charge normal',  336,  NULL, 27.62),
    (1, 'energy',    'Energy charge reduced', NULL, NULL, 14.68),
    (1, 'energy',    'Fixed charge',          NULL, NULL,  4.67),

    (1, 'regulated', 'ADMIE',                 NULL, NULL,  2.85),
    (1, 'regulated', 'DEDDIE',                NULL, NULL,  4.78),
    (1, 'regulated', 'YKO',                   NULL, NULL,  1.96),
    (1, 'regulated', 'ETMEAR',                NULL, NULL,  4.85),

    (1, 'taxes',     'Municipality DT',       NULL, NULL, 16.00),
    (1, 'taxes',     'Municipality DF',       NULL, NULL,  3.77),
    (1, 'taxes',     'TAP',                   NULL, NULL,  3.48),
    (1, 'taxes',     'ERT',                   NULL, NULL,  2.76),

    (1, 'other',     'EFK',                   NULL, NULL,  0.63),
    (1, 'other',     'EID Tel',               NULL, NULL,  0.29),
    (1, 'other',     'Late interest',         NULL, NULL,  0.75),
    (1, 'other',     'Paper bill charge',     NULL, NULL,  0.03),
    (1, 'other',     'Rounding',              NULL, NULL,  0.21),
    (1, 'other',     'Previous rounding',     NULL, NULL, -0.05),

    (1, 'taxes',     'VAT 6%',                NULL, NULL,  3.72);

INSERT INTO Customer_Context (
    customer_id, contract_id, account_id,
    active_tariff, segment, region,
    avg_kwh_6m, last_3_bills_total
) VALUES (
    1, 1, '1476458196',
    'Γ1Ν', 'residential', 'Unknown',
    336, 182.00
);
"""


def init():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")

    # Create schema
    conn.executescript(DDL)

    # Seed only if empty
    row_count = conn.execute("SELECT COUNT(*) FROM Billing_Header").fetchone()[0]
    if row_count == 0:
        conn.executescript(SEED_SQL)
        print("✅ Seeded initial data.")
    else:
        print(f"ℹ️  Billing_Header already has {row_count} row(s) — skipping seed.")

    conn.commit()

    # Quick verification
    print(f"\n📂 Database: {DB_PATH}")
    print(f"   Billing_Header rows  : {conn.execute('SELECT COUNT(*) FROM Billing_Header').fetchone()[0]}")
    print(f"   Billing_Lines rows   : {conn.execute('SELECT COUNT(*) FROM Billing_Lines').fetchone()[0]}")
    print(f"   Customer_Context rows: {conn.execute('SELECT COUNT(*) FROM Customer_Context').fetchone()[0]}")

    print("\n--- Billing_Header ---")
    for row in conn.execute("SELECT * FROM Billing_Header"):
        print(" ", row)

    print("\n--- Billing_Lines ---")
    for row in conn.execute("SELECT * FROM Billing_Lines"):
        print(" ", row)

    print("\n--- Customer_Context ---")
    for row in conn.execute("SELECT * FROM Customer_Context"):
        print(" ", row)

    conn.close()


if __name__ == "__main__":
    init()

