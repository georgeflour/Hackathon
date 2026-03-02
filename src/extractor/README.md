# Step 2 — Extractor Module

Location: `src/extractor/`

This module handles **Step 1** of the pipeline: converting a bill image into a structured JSON entity. It is used by `VisionAgent` (Agent 1) as its rule-based fallback when no `OPENAI_API_KEY` is set.

---

## Files to create

| File | Purpose |
|---|---|
| `src/extractor/__init__.py` | empty — makes it a package |
| `src/extractor/ocr.py` | Tesseract OCR wrapper |
| `src/extractor/parser.py` | Rule-based field extractor |
| `src/extractor/tests/__init__.py` | empty |
| `src/extractor/tests/test_parser.py` | Unit tests |

---

## `ocr.py`

### What it does
Wraps `pytesseract` to convert a bill image file to raw text + a confidence score.

### Interface

```python
@dataclass
class OcrResult:
    raw_text: str
    confidence: float   # 0.0 – 1.0

def run_ocr(image_path: str | Path) -> OcrResult:
    ...
```

### Implementation notes
- Open the image with `PIL.Image.open`.
- Call `pytesseract.image_to_string` for text.
- Call `pytesseract.image_to_data(..., output_type=Output.DICT)` to get per-word confidence scores; average the non-negative values and divide by 100.
- If `pytesseract` is not installed raise `ImportError` with a message: `"pip install pytesseract Pillow && brew install tesseract"`.

---

## `parser.py`

### What it does
Parses raw OCR text (or any bill-like string) into the `ExtractedBill` dict defined in `schemas/extracted_bill_example.json`.

### Output shape

```python
{
  "extracted_id": str,                  # uuid4
  "extraction_timestamp": str,          # ISO 8601 UTC
  "ocr_confidence": float,
  "extraction_method": "rule_based",
  "bill_number":     {"value": str|None, "confidence": float},
  "account_number":  {"value": str|None, "normalized": str|None, "confidence": float},
  "customer_name":   {"value": str|None, "normalized": str|None, "confidence": float},
  "customer_address": [str],
  "bill_date":       {"value": str|None, "confidence": float},
  "service_period":  {"start": str|None, "end": str|None, "confidence": float},
  "total_due":       {"value": float|None, "currency": str, "confidence": float},
  "line_items": [
    {"description": str, "quantity_kwh": float|None, "unit_price": float|None, "amount": float|None}
  ],
  "meter_ids": [str],
  "tariff_code": str|None,
  "match_hints": {"account_hash": str|None, "name_norm": str|None, "meter_list": [str]}
}
```

### Regex patterns to implement

| Field | Pattern hint |
|---|---|
| `account_number` | Look for `account`, `acc no`, `account number`, `account #` followed by 6–20 digits |
| `bill_number` | Look for `bill`, `invoice`, `document` followed by an alphanumeric code |
| `customer_name` | Look for `customer`, `client`, `name` followed by 2–50 characters |
| `meter_ids` | Look for `meter`, `mtr` followed by an alphanumeric ID |
| `bill_date` | Look for `bill date`, `invoice date`, `issue date` followed by a date |
| `period_from` | Look for `from`, `period from`, `service from` followed by a date |
| `period_to` | Look for `to`, `period to`, `service to` followed by a date |
| `total_due` | Look for `total`, `amount due`, `total due`, `payable` — handle currency symbol before OR after amount |
| `line_items` | Pattern match for `energy consumption`, `regulated charges`, `taxes` rows with optional kWh + rate + amount |
| `tariff_code` | Look for `tariff`, `rate code`, `plan` followed by alphanumeric like `T01` |

### Helper functions to implement

```python
def _first(pattern, text, flags=re.IGNORECASE) -> str | None
def _find_all(pattern, text, flags=re.IGNORECASE) -> list[str]
def _normalize_digits(value) -> str | None        # strip non-digits
def _normalize_name(value) -> str | None          # lowercase + strip whitespace
def _parse_amount(value) -> float | None          # handle comma decimals

def extract_fields(raw_text: str, ocr_confidence: float = 1.0) -> dict
```

---

## `tests/test_parser.py`

Use this sample text for all tests:

```
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
```

### Tests to write

| Test | Assertion |
|---|---|
| `test_extract_account_number` | `result["account_number"]["normalized"] == "123456789"` |
| `test_extract_total_due` | `result["total_due"]["value"] == 152.34` |
| `test_extract_meter_ids` | `"MTR-987" in result["meter_ids"]` |
| `test_extract_line_items` | energy line has `quantity_kwh == 420.0` |
| `test_extract_service_period` | `start` and `end` are not None |
| `test_extract_customer_name` | `"john doe" in result["customer_name"]["normalized"]` |
| `test_extract_tariff_code` | `result["tariff_code"] == "T01"` |

Run with: `python -m pytest src/extractor/tests -v`

---

## Validation checklist

- [ ] `ocr.py` — `OcrResult` dataclass + `run_ocr` function
- [ ] `parser.py` — `extract_fields` returns all fields in the output shape above
- [ ] Handles `EUR 152.34` AND `152.34 EUR` AND `€152.34` for total_due
- [ ] `normalized` account number is digits-only
- [ ] All 7 tests pass

---

## Next step → `src/matcher/README.md`

