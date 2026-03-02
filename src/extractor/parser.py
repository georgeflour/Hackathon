"""
extractor/parser.py
-------------------
Rule-based field extractor.

Takes raw OCR text (or any bill-like string) → returns a structured
ExtractedBill dict that matches schemas/extracted_bill_example.json.

No external ML dependencies — pure regex so results are deterministic
and testable without a GPU or API key.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any


# ─── low-level helpers ────────────────────────────────────────────────────────

def _first(pattern: str, text: str, flags: int = re.IGNORECASE) -> str | None:
    """Return the first capturing group of the first match, or None."""
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _find_all(pattern: str, text: str, flags: int = re.IGNORECASE) -> list[str]:
    """Return all non-overlapping matches of the first capturing group."""
    return re.findall(pattern, text, flags)


def _normalize_digits(value: str | None) -> str | None:
    """Strip everything except digits."""
    if value is None:
        return None
    result = re.sub(r"[^0-9]", "", value)
    return result if result else None


def _normalize_name(value: str | None) -> str | None:
    """Lowercase + collapse whitespace."""
    if value is None:
        return None
    return re.sub(r"\s+", " ", value.lower().strip())


def _parse_amount(value: str | None) -> float | None:
    """Parse a decimal string that may use comma as decimal separator."""
    if value is None:
        return None
    # Remove everything except digits, commas, dots
    cleaned = re.sub(r"[^\d,.]", "", value)
    if not cleaned:
        return None
    # If both comma and dot appear treat comma as thousands separator
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    else:
        # Lone comma → decimal separator
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _conf(value: Any) -> float:
    """Return a fixed confidence value based on whether extraction succeeded."""
    return 0.95 if value is not None else 0.0


# ─── line-item extraction ─────────────────────────────────────────────────────

# Each pattern tries to capture: description, optional kWh, optional rate, amount
_LINE_PATTERNS: list[tuple[str, list[str]]] = [
    # "Energy consumption  420 kWh  0.12  50.40"
    (
        r"(energy\s+\w+)\s+([\d.,]+)\s*kwh\s+([\d.,]+)\s+([\d.,]+)",
        ["description", "quantity_kwh", "unit_price", "amount"],
    ),
    # "Regulated charges  30.00"
    (
        r"(regulated[\w\s]+?)\s{2,}([\d.,]+)\s*(?:eur)?$",
        ["description", "amount"],
    ),
    # "Taxes  71.94"  /  "VAT  71.94"
    (
        r"(taxes|vat\s*\d*%?|φπα)\s{2,}([\d.,]+)\s*(?:eur)?$",
        ["description", "amount"],
    ),
]


def _extract_line_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for pattern, fields in _LINE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            groups = m.groups()
            desc = groups[0].strip().lower()
            if desc in seen:
                continue
            seen.add(desc)

            item: dict[str, Any] = {
                "description": desc,
                "quantity_kwh": None,
                "unit_price": None,
                "amount": None,
            }
            for i, field in enumerate(fields):
                item[field] = _parse_amount(groups[i]) if field != "description" else groups[i].strip().lower()
            items.append(item)

    return items


# ─── main extractor ───────────────────────────────────────────────────────────

def extract_fields(raw_text: str, ocr_confidence: float = 1.0) -> dict[str, Any]:
    """
    Parse raw OCR / bill text into a structured ExtractedBill dictionary.

    Parameters
    ----------
    raw_text       : plain text output from OCR (or a synthetic bill string)
    ocr_confidence : confidence score from the OCR engine (0.0 – 1.0)

    Returns
    -------
    dict matching schemas/extracted_bill_example.json
    """
    extracted_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # ── account number ────────────────────────────────────────────────────────
    account_raw = _first(
        r"(?:account|acc(?:ount)?\.?\s*(?:no|number|#|nr)?)[:\s#.]*(\d{6,20})",
        raw_text,
    )

    # ── bill / invoice number ─────────────────────────────────────────────────
    bill_number_raw = _first(
        r"(?:bill|invoice|document)\s*(?:no|number|#|nr)?[:\s]*([A-Z0-9][\w\-/]{3,20})",
        raw_text,
    )

    # ── customer name ─────────────────────────────────────────────────────────
    customer_name_raw = _first(
        r"(?:customer|client|name)[:\s]+([A-Za-z][A-Za-z '\-\.]{2,50}?)(?:\n|$)",
        raw_text,
    )

    # ── address ───────────────────────────────────────────────────────────────
    address_match = re.search(
        r"(?:address|billing\s+address)[:\s]+(.+?)(?:\n|$)", raw_text, re.IGNORECASE
    )
    customer_address = [address_match.group(1).strip()] if address_match else []

    # ── meter IDs ─────────────────────────────────────────────────────────────
    meter_ids = _find_all(r"(?:meter|mtr)[:\s#\-]*([\w\-]{3,20})", raw_text)
    # Deduplicate while preserving order
    meter_ids = list(dict.fromkeys(meter_ids))

    # ── tariff code ───────────────────────────────────────────────────────────
    tariff_raw = _first(
        r"(?:tariff|rate\s+code|plan|rate)[:\s]+([A-Z]\d{1,4}(?:[A-Z]\d*)?)",
        raw_text,
    )

    # ── dates ─────────────────────────────────────────────────────────────────
    _date_pat = r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"

    bill_date_raw = _first(
        rf"(?:bill|invoice|issue)\s*date[:\s]*{_date_pat}",
        raw_text,
    )
    period_from_raw = _first(
        rf"(?:period\s+from|service\s+from|from)[:\s]*{_date_pat}",
        raw_text,
    )
    period_to_raw = _first(
        rf"(?:period\s+to|service\s+to|[^\w]to)[:\s]*{_date_pat}",
        raw_text,
    )

    # ── total due ─────────────────────────────────────────────────────────────
    # Handle: "Total Due: EUR 152.34", "Total: 152.34 EUR", "€152.34"
    total_raw = _first(
        r"(?:total\s+due|total\s+amount|amount\s+due|payable|total)[:\s]*(?:[€$£]|EUR|USD|GBP)?\s*([\d.,]{2,12})",
        raw_text,
    )
    if not total_raw:
        # Fallback: currency symbol / code followed by amount
        total_raw = _first(r"(?:EUR|USD|GBP|[€$£])\s*([\d.,]{2,12})", raw_text)

    # ── line items ────────────────────────────────────────────────────────────
    line_items = _extract_line_items(raw_text)

    # ── assemble result ───────────────────────────────────────────────────────
    return {
        "extracted_id": extracted_id,
        "extraction_timestamp": now,
        "ocr_confidence": ocr_confidence,
        "extraction_method": "rule_based",
        "bill_number": {
            "value": bill_number_raw,
            "confidence": _conf(bill_number_raw),
        },
        "account_number": {
            "value": account_raw,
            "normalized": _normalize_digits(account_raw),
            "confidence": _conf(account_raw),
        },
        "customer_name": {
            "value": customer_name_raw,
            "normalized": _normalize_name(customer_name_raw),
            "confidence": _conf(customer_name_raw),
        },
        "customer_address": customer_address,
        "bill_date": {
            "value": bill_date_raw,
            "confidence": _conf(bill_date_raw),
        },
        "service_period": {
            "start": period_from_raw,
            "end": period_to_raw,
            "confidence": _conf(period_from_raw) if period_from_raw and period_to_raw else 0.3,
        },
        "total_due": {
            "value": _parse_amount(total_raw),
            "currency": "EUR",
            "confidence": _conf(total_raw),
        },
        "line_items": line_items,
        "meter_ids": meter_ids,
        "tariff_code": tariff_raw,
        "match_hints": {
            "account_hash": _normalize_digits(account_raw),
            "name_norm": _normalize_name(customer_name_raw),
            "meter_list": meter_ids,
        },
    }

