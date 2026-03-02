# Step 3 — Matcher Module

Location: `src/matcher/`

This module handles **Step 2** of the pipeline: matching an extracted bill to a customer row in the DWH `Customer_Context.csv`.

---

## Files to create

| File | Purpose |
|---|---|
| `src/matcher/__init__.py` | empty |
| `src/matcher/match_service.py` | core matching logic |
| `src/matcher/tests/__init__.py` | empty |
| `src/matcher/tests/test_match_service.py` | unit tests |

---

## `match_service.py`

### Data types

```python
@dataclass
class Candidate:
    customer_id: str
    customer_name: str
    score: float          # 0.0 – 1.0
    match_field: str      # which field drove the match

@dataclass
class MatchResult:
    match_type: str                   # "exact" | "fuzzy_high" | "fuzzy_ambiguous" | "none"
    matched_customer_id: str | None
    score: float
    candidates: list[Candidate]
    clarifying_question: str | None
```

### Public function

```python
def match_customer(
    extracted: dict,
    csv_path: Path = DEFAULT_CUSTOMER_CSV,
) -> MatchResult:
    ...
```

### Matching algorithm — implement in this order

**Step 1 — Load DWH**

Load `Customer_Context.csv` with `pd.read_csv(..., dtype=str)`.
Compute normalised columns on load:
- `_account_norm` = `account_numbers` stripped to digits only
- `_primary_norm` = `primary_account` stripped to digits only
- `_name_norm` = `customer_name` lowercased + stripped
- `_addr_norm` = `addresses` lowercased + stripped
- `_meters_raw` = `service_meters` as-is

**Step 2 — Exact account number match** (score 0.99)

Normalise `extracted["account_number"]["normalized"]` to digits.
Compare against `_account_norm` and `_primary_norm` for every row.
If exactly one row matches → return `MatchResult(match_type="exact", score=0.99)`.

**Step 3 — Exact meter ID match** (score 0.97)

Compare `extracted["meter_ids"]` against `_meters_raw` (use regex `findall` to get tokens).
If one row has any overlapping meter → return `MatchResult(match_type="exact", score=0.97)`.

**Step 4 — Exact normalised name + address** (score 0.95)

Compare normalised customer name AND check if normalised address is contained in `_addr_norm`.
If match → return `MatchResult(match_type="exact", score=0.95)`.

**Step 5 — Fuzzy fallback** (rapidfuzz)

For every row compute:
```
name_score    = fuzz.token_set_ratio(name_norm, row._name_norm) / 100
addr_score    = fuzz.token_set_ratio(addr_norm, row._addr_norm) / 100
meter_score   = 1.0 if meter overlap else 0.0
final_score   = 0.6 * name_score + 0.3 * addr_score + 0.1 * meter_score
```

Sort candidates descending by `final_score`. Then:
- `>= 0.90` → `match_type = "fuzzy_high"`, return top candidate
- `0.75 – 0.90` → `match_type = "fuzzy_ambiguous"`, return top 3 + generate clarifying question
- `< 0.75` → `match_type = "none"`

**Clarifying question template:**
```
"We found multiple possible matches. Which customer matches this bill?
  A) {name} — {address}
  B) {name} — {address}
  C) {name} — {address}
  D) None of these"
```

### Important implementation notes

- Always load CSV with `dtype=str` to prevent `123456789` being read as an integer.
- The `customer_id` column in the CSV is the real ID (e.g. `cust-42`) — return this, not the account number.
- `_norm_digits(value)` = `re.sub(r"[^0-9]", "", str(value or ""))`
- `_norm(value)` = `re.sub(r"\s+", " ", str(value or "").lower().strip())`

---

## `tests/test_match_service.py`

### Sample extracted dict for tests

```python
EXACT = {
    "account_number": {"value": "123456789", "normalized": "123456789"},
    "customer_name":  {"normalized": "john doe"},
    "customer_address": ["1 Main St Athens"],
    "meter_ids": ["MTR-987"],
}
```

### Tests to write

| Test | Assertion |
|---|---|
| `test_exact_account_match` | `match_type == "exact"`, `matched_customer_id == "cust-42"`, `score >= 0.95` |
| `test_meter_match` | match via meter ID when account is None |
| `test_no_match` | `match_type == "none"` for unknown account + name |
| `test_fuzzy_ambiguous_returns_question` | `clarifying_question is not None` for ambiguous input |
| `test_match_result_has_customer_id_not_account_number` | `matched_customer_id` starts with `"cust-"` |

Run with: `python -m pytest src/matcher/tests -v`

---

## Validation checklist

- [ ] `MatchResult` and `Candidate` dataclasses defined
- [ ] All 5 matching steps implemented in order
- [ ] Exact match returns `customer_id` from the CSV (`cust-42`), not account number
- [ ] Fuzzy ambiguous produces a readable clarifying question string
- [ ] All 5 tests pass

---

## Next step → `src/retriever/README.md`

