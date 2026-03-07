"""
data/dwh/init_customers_bills_db.py
------------------------------------
Creates and seeds the local SQLite customers_bills.db based on sql.txt
(Customers + Bills tables).

Run once:
    python data/dwh/init_customers_bills_db.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "customers_bills.db"

DDL = """
CREATE TABLE IF NOT EXISTS Customers (
    Arxikos_Paroxis INTEGER PRIMARY KEY,
    Name            TEXT,
    EmployeeOrPensioner TEXT,
    AFM             INTEGER,
    Street          TEXT,
    StreetNumber    TEXT,
    City            TEXT,
    InvoiceCode     TEXT,
    UsageType       TEXT,
    BillFrequency   TEXT,
    TarifShort      TEXT,
    TarifAnal       TEXT
);

CREATE TABLE IF NOT EXISTS Bills (
    Arxikos_Paroxis     INTEGER PRIMARY KEY,
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
    AccountNumber       TEXT,
    CONSTRAINT FK_Bills_Customers
        FOREIGN KEY (Arxikos_Paroxis)
        REFERENCES Customers(Arxikos_Paroxis)
);
"""

SEED_CUSTOMERS = [
    (483905721684, 'Δημήτρης Παπαδόπουλος', 'Μισθωτός',    483905721, 'ΛΕΩΦΟΡΟΣ ΚΗΦΙΣΙΑΣ', '124', 'ΜΑΡΟΥΣΙ',      'LVO4F', 'ΟΙΚΙΑΚΗ', 'Μ', 'myHome4 Plan',          '~myHome4 Plan ~4F~χωρχρο'),
    (917264038552, 'Μαρία Κωνσταντίνου',     'Συνταξιούχος', 761209483, 'ΕΓΝΑΤΙΑΣ',          '56',  'ΘΕΣΣΑΛΟΝΙΚΗ',  'LVO4A', 'ΟΙΚΙΑΚΗ', 'Μ', 'ΟΙΚΙΑΚΟ – MyHome 4All', '~myHome4All~4All~χωρχρο'),
    (650182947331, 'Γεώργιος Αντωνίου',      'Μισθωτός',    492650138, 'ΑΡΙΣΤΟΜΕΝΟΥΣ',      '89',  'ΚΑΛΑΜΑΤΑ',     'LVOXM', 'ΟΙΚΙΑΚΗ', 'Μ', 'ΟΙΚΙΑΚΟ',               'Γ1Ν~Οικιακό Τιμολόγιο~με χρονοχρέωση 1Φ'),
]

SEED_BILLS = [
    (483905721684, '2 ΕΚΚΑΘ/ΚΟΣ', 412, 127.64, '2026-01-19', '2026-02-15', 54.32, 28.14, 12.50, 7.80,  24.88, 0.00, 127.64, 127.64, '20260318001'),
    (917264038552, '2 ΕΚΚΑΘ/ΚΟΣ', 285, 100.55, '2026-01-19', '2026-02-15', 38.75, 21.63, 10.00, 6.45,  18.52, 5.20, 100.55, 100.55, '20260318002'),
    (650182947331, '2 ΕΚΚΑΘ/ΚΟΣ', 503, 147.19, '2026-01-19', '2026-02-15', 61.40, 33.22, 15.00, 9.10,  28.47, 0.00, 147.19, 147.19, '20260318003'),
]


def init():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(DDL)

    # Seed only if empty
    if conn.execute("SELECT COUNT(*) FROM Customers").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO Customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            SEED_CUSTOMERS,
        )
        conn.executemany(
            "INSERT INTO Bills VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            SEED_BILLS,
        )
        conn.commit()
        print("✅ Seeded initial data.")
    else:
        print("ℹ️  Tables already have data — skipping seed.")

    # Verification
    print(f"\n📂 Database : {DB_PATH}")
    print(f"   Customers : {conn.execute('SELECT COUNT(*) FROM Customers').fetchone()[0]} rows")
    print(f"   Bills     : {conn.execute('SELECT COUNT(*) FROM Bills').fetchone()[0]} rows")

    print("\n--- Customers ---")
    for row in conn.execute("SELECT Arxikos_Paroxis, Name, City, TarifShort FROM Customers"):
        print(f"   {row[0]}  {row[1]}  ({row[2]})  [{row[3]}]")

    print("\n--- Bills ---")
    for row in conn.execute(
        "SELECT b.Arxikos_Paroxis, c.Name, b.Consumption, b.SynoloPoso, b.AccountNumber "
        "FROM Bills b JOIN Customers c USING (Arxikos_Paroxis)"
    ):
        print(f"   {row[0]}  {row[1]}  {row[2]} kWh  €{row[3]}  #{row[4]}")

    conn.close()


if __name__ == "__main__":
    init()

