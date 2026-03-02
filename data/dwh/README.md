# Step 0 — Mock DWH Data

This folder contains the simulated Data Warehouse (DWH) CSV files that replace a real SAP/database backend during the hackathon.

## Files to create

| File | DWH Table | Description |
|---|---|---|
| `Billing_Header.csv` | `Billing_Header` | One row per bill — header-level info |
| `Billing_Lines.csv` | `Billing_Lines` | Line-item charges per bill |
| `Customer_Context.csv` | `Customer_Context` | Customer profile + consumption history |

---

## Billing_Header.csv

Columns (match `schemas/billing_header.json`):

```
billing_id, issue_date, period_from, period_to, customer_id, contract_id,
account_id, supply_number, tariff_code, total_amount, currency
```

Rules:
- `billing_id` — unique string, e.g. `B-2026-0001`
- `issue_date`, `period_from`, `period_to` — ISO date `YYYY-MM-DD`
- `customer_id` — FK to `Customer_Context.customer_id`
- `account_id` — the account number shown on the bill (plain digits, no brackets)
- `total_amount` — decimal number
- `currency` — `EUR`

Create at least **4 rows**: 2 bills for one residential customer, 1 for a business customer, 1 for an unknown customer (no matching context row) to cover all demo scenarios.

---

## Billing_Lines.csv

Columns (match `schemas/billing_lines.json`):

```
line_id, billing_id, charge_type, description, quantity_kwh, unit_price, amount, unit
```

Rules:
- `line_id` — unique, e.g. `L-001`
- `billing_id` — FK to `Billing_Header.billing_id`
- `charge_type` — one of: `energy`, `regulated`, `taxes`, `other`
- `quantity_kwh` — leave empty for non-energy lines
- `unit_price` — leave empty for non-energy lines
- `amount` — decimal
- `unit` — `kWh` for energy lines, `EUR` otherwise

Create 3 lines per bill: one `energy`, one `regulated`, one `taxes`.

---

## Customer_Context.csv

Columns (match `schemas/customer_context.json`):

```
customer_id, account_numbers, primary_account, customer_name, addresses,
service_meters, active_tariff, segment, region, avg_kwh_6m, last_3_bills_total
```

Rules:
- `customer_id` — unique string, e.g. `cust-42`
- `account_numbers` — **plain digit string** (no JSON brackets, no quotes) matching what appears on the bill
- `primary_account` — same plain digit string as the main account
- `customer_name` — full name
- `addresses` — plain text, e.g. `1 Main St Athens`
- `service_meters` — meter ID, e.g. `MTR-987`
- `active_tariff` — e.g. `T01`
- `segment` — `residential` or `business`
- `avg_kwh_6m` — average monthly consumption over last 6 months (integer)
- `last_3_bills_total` — sum of last 3 bills (decimal)

Create at least **2 customers**: one residential, one business.

> ⚠️ Do NOT use JSON arrays (e.g. `["123"]`) in any column — use plain text so pandas reads the CSV without parsing issues.

---

## Loading in Python

```python
import pandas as pd

header = pd.read_csv("data/dwh/Billing_Header.csv", dtype=str)
lines  = pd.read_csv("data/dwh/Billing_Lines.csv",  dtype=str)
ctx    = pd.read_csv("data/dwh/Customer_Context.csv", dtype=str)
```

Always load with `dtype=str` to prevent pandas from misreading account numbers as integers.

---

## Validation checklist

- [ ] `Billing_Header.csv` exists with ≥ 4 rows
- [ ] `Billing_Lines.csv` exists with ≥ 3 lines per bill
- [ ] `Customer_Context.csv` exists with ≥ 2 customer rows
- [ ] No JSON arrays in any CSV cell
- [ ] `account_id` in `Billing_Header` matches `primary_account` in `Customer_Context` for known customers
- [ ] Dates are `YYYY-MM-DD`

---

## Next step → `data/knowledge/README.md`

