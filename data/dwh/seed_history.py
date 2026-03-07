"""
data/dwh/seed_history.py
------------------------
1. Migrates Bills table to use AccountNumber as PRIMARY KEY
   (allows multiple bills per customer / Arxikos_Paroxis)
2. Inserts 9 historical bill rows (Jan / Nov / Dec 2025)

Run:
    python data/dwh/seed_history.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "customers_bills.db"


def migrate_and_seed():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = OFF")

    # ── 1. Check if migration is needed ───────────────────────────
    pk_col = conn.execute(
        "SELECT name FROM pragma_table_info('Bills') WHERE pk = 1"
    ).fetchone()

    if pk_col and pk_col[0] == "Arxikos_Paroxis":
        print("🔄 Migrating Bills: changing PRIMARY KEY from Arxikos_Paroxis → AccountNumber ...")
        conn.executescript("""
            ALTER TABLE Bills RENAME TO Bills_old;

            CREATE TABLE Bills (
                AccountNumber       TEXT PRIMARY KEY,
                Arxikos_Paroxis     INTEGER NOT NULL,
                Category            TEXT,
                Consumption         INTEGER,
                SynoloPoso          REAL,
                FromDate            TEXT,
                ToDate              TEXT,
                Charge_DEH          REAL,
                RegulatedCharges    REAL,
                AgainstConsumption  REAL,
                Misc                REAL,
                VAT                 REAL,
                PreviousUnpaid      REAL,
                TotalPayment        REAL,
                PaymentAmount       REAL,
                CONSTRAINT FK_Bills_Customers
                    FOREIGN KEY (Arxikos_Paroxis)
                    REFERENCES Customers(Arxikos_Paroxis)
            );

            INSERT INTO Bills
                SELECT AccountNumber, Arxikos_Paroxis, Category, Consumption, SynoloPoso,
                       FromDate, ToDate, Charge_DEH, RegulatedCharges, AgainstConsumption,
                       Misc, VAT, PreviousUnpaid, TotalPayment, PaymentAmount
                FROM Bills_old;

            DROP TABLE Bills_old;
        """)
        conn.commit()
        print("✅ Migration done.")
    else:
        print("ℹ️  Bills table already has AccountNumber as PK — skipping migration.")

    # ── 2. Insert historical bills ─────────────────────────────────
    new_bills = [
        # Nov 2025
        ('20251118001', 483905721684, '2 ΕΚΚΑΘ/ΚΟΣ', 405, 125.30, '2025-11-19', '2025-12-18', 51.50, 27.50, 12.30, 7.70, 26.00, 0.00, 125.30, 125.30),
        ('20251118002', 917264038552, '2 ΕΚΚΑΘ/ΚΟΣ', 275,  96.50, '2025-11-19', '2025-12-18', 36.80, 20.80, 10.00, 6.10, 22.80, 1.80,  96.50,  96.50),
        ('20251118003', 650182947331, '2 ΕΚΚΑΘ/ΚΟΣ', 495, 146.50, '2025-11-19', '2025-12-18', 61.50, 33.00, 15.00, 9.00, 28.00, 0.00, 146.50, 146.50),
        # Dec 2025
        ('20251218001', 483905721684, '2 ΕΚΚΑΘ/ΚΟΣ', 398, 123.50, '2025-12-19', '2026-01-18', 52.00, 27.00, 12.00, 7.50, 25.00, 0.00, 123.50, 123.50),
        ('20251218002', 917264038552, '2 ΕΚΚΑΘ/ΚΟΣ', 290,  98.00, '2025-12-19', '2026-01-18', 37.50, 21.00, 10.50, 6.00, 23.00, 2.00,  98.00,  98.00),
        ('20251218003', 650182947331, '2 ΕΚΚΑΘ/ΚΟΣ', 510, 149.00, '2025-12-19', '2026-01-18', 62.00, 34.00, 15.50, 9.00, 28.50, 0.00, 149.00, 149.00),
        # Jan 2025
        ('20250118001', 483905721684, '2 ΕΚΚΑΘ/ΚΟΣ', 400, 120.00, '2025-01-19', '2025-02-15', 50.00, 26.00, 12.00, 6.50, 25.50, 0.00, 120.00, 120.00),
        ('20250118002', 917264038552, '2 ΕΚΚΑΘ/ΚΟΣ', 280,  95.00, '2025-01-19', '2025-02-15', 36.50, 20.50, 10.00, 6.00, 22.50, 1.50,  95.00,  95.00),
        ('20250118003', 650182947331, '2 ΕΚΚΑΘ/ΚΟΣ', 500, 145.00, '2025-01-19', '2025-02-15', 60.00, 32.50, 15.00, 9.00, 28.50, 0.00, 145.00, 145.00),
    ]

    conn.executemany("""
        INSERT OR IGNORE INTO Bills
        (AccountNumber, Arxikos_Paroxis, Category, Consumption, SynoloPoso,
         FromDate, ToDate, Charge_DEH, RegulatedCharges, AgainstConsumption,
         Misc, VAT, PreviousUnpaid, TotalPayment, PaymentAmount)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, new_bills)
    conn.commit()

    # ── 3. Verify ──────────────────────────────────────────────────
    total = conn.execute("SELECT COUNT(*) FROM Bills").fetchone()[0]
    print(f"\n✅ Done. Total Bills rows: {total}")
    print()
    print(f"  {'AccountNumber':<16} {'Arxikos_Paroxis':<16} {'Period':<30} {'€':>8}")
    print("  " + "-" * 72)
    for row in conn.execute("""
        SELECT AccountNumber, Arxikos_Paroxis, FromDate, ToDate, SynoloPoso
        FROM Bills ORDER BY Arxikos_Paroxis, FromDate
    """):
        print(f"  {row[0]:<16} {row[1]:<16} {row[2]} → {row[3]}   €{row[4]:>8.2f}")

    conn.close()


if __name__ == "__main__":
    migrate_and_seed()

