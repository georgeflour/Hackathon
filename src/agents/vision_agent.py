"""
agents/vision_agent.py  —  Agent 1: Vision & Data Extraction
-------------------------------------------------------------
Converts a bill image → structured ExtractedBill JSON.

Strategy:
  1. If OPENAI_API_KEY is set  → call GPT-4o vision (multimodal)
  2. Fallback                  → Tesseract OCR + rule-based regex parser
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─── result type ─────────────────────────────────────────────────────────────

@dataclass
class VisionResult:
    extracted: dict[str, Any]
    ocr_confidence: float
    extraction_method: str          # "llm_vision" | "rule_based"
    agent_name: str = "VisionAgent"


# ─── GPT-4o vision system prompt ─────────────────────────────────────────────

VISION_SYSTEM_PROMPT = """You are an expert OCR and data-extraction assistant for electricity bills.
Given a bill image, extract the following fields and return ONLY valid JSON — no markdown, no explanation:

{
  "bill_number": "string or null",
  "account_number": "string or null",
  "customer_name": "string or null",
  "customer_address": ["list of address lines"],
  "bill_date": "YYYY-MM-DD or null",
  "service_period_start": "YYYY-MM-DD or null",
  "service_period_end": "YYYY-MM-DD or null",
  "total_due_value": "number or null",
  "total_due_currency": "string or null",
  "meter_ids": ["list of meter IDs"],
  "tariff_code": "string or null",
  "line_items": [
    {
      "description": "string",
      "quantity_kwh": "number or null",
      "unit_price": "number or null",
      "amount": "number or null"
    }
  ]
}

Rules:
- Return ONLY valid JSON. No markdown fences.
- Use null for any field you cannot find.
- Dates must be YYYY-MM-DD format.
- account_number should be the digits-only account or customer number shown on the bill."""


# ─── normalise GPT-4o output → internal schema ───────────────────────────────

def _normalise_llm_output(
    raw: dict[str, Any],
    ocr_confidence: float,
) -> dict[str, Any]:
    """Map GPT-4o field names → ExtractedBill schema."""

    def _conf(v: Any) -> float:
        return 0.97 if v is not None else 0.0

    def _digits(v: Any) -> str | None:
        if v is None:
            return None
        import re
        r = re.sub(r"[^0-9]", "", str(v))
        return r or None

    line_items = raw.get("line_items") or []

    return {
        "extracted_id":         str(uuid.uuid4()),
        "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
        "ocr_confidence":       ocr_confidence,
        "extraction_method":    "llm_vision",
        "bill_number":          {"value": raw.get("bill_number"),     "confidence": _conf(raw.get("bill_number"))},
        "account_number":       {
            "value":      raw.get("account_number"),
            "normalized": _digits(raw.get("account_number")),
            "confidence": _conf(raw.get("account_number")),
        },
        "customer_name":        {
            "value":      raw.get("customer_name"),
            "normalized": (raw.get("customer_name") or "").lower().strip() or None,
            "confidence": _conf(raw.get("customer_name")),
        },
        "customer_address":     raw.get("customer_address") or [],
        "bill_date":            {"value": raw.get("bill_date"),               "confidence": _conf(raw.get("bill_date"))},
        "service_period":       {
            "start":      raw.get("service_period_start"),
            "end":        raw.get("service_period_end"),
            "confidence": _conf(raw.get("service_period_start")),
        },
        "total_due":            {
            "value":      raw.get("total_due_value"),
            "currency":   raw.get("total_due_currency") or "EUR",
            "confidence": _conf(raw.get("total_due_value")),
        },
        "line_items":           [
            {
                "description":  li.get("description", ""),
                "quantity_kwh": li.get("quantity_kwh"),
                "unit_price":   li.get("unit_price"),
                "amount":       li.get("amount"),
            }
            for li in line_items
        ],
        "meter_ids":            raw.get("meter_ids") or [],
        "tariff_code":          raw.get("tariff_code"),
        "match_hints":          {
            "account_hash": _digits(raw.get("account_number")),
            "name_norm":    (raw.get("customer_name") or "").lower().strip() or None,
            "meter_list":   raw.get("meter_ids") or [],
        },
    }


# ─── LLM vision call ─────────────────────────────────────────────────────────

def _llm_vision_extract(image_path: Path) -> dict[str, Any] | None:
    """Call GPT-4o with the bill image as base64. Returns raw dict or None on failure."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        suffix = image_path.suffix.lower().lstrip(".")
        mime   = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
        b64    = base64.b64encode(image_path.read_bytes()).decode("utf-8")

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            temperature=0,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {"role": "user",   "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception:
        return None


# ─── rule-based fallback ──────────────────────────────────────────────────────

def _rule_based_extract(image_path: Path) -> tuple[dict[str, Any], float]:
    """OCR + regex. Returns (extracted_dict, ocr_confidence)."""
    from src.extractor.parser import extract_fields

    # Try Tesseract first
    try:
        from src.extractor.ocr import run_ocr
        ocr = run_ocr(image_path)
        extracted = extract_fields(ocr.raw_text, ocr.confidence)
        return extracted, ocr.confidence
    except (ImportError, Exception):
        pass

    # If the file is a plain text file (useful for tests), read it directly
    try:
        text = image_path.read_text(errors="ignore")
        extracted = extract_fields(text, ocr_confidence=0.5)
        return extracted, 0.5
    except Exception:
        pass

    # Last resort — return empty extraction
    extracted = extract_fields("", ocr_confidence=0.0)
    return extracted, 0.0


# ─── public interface ─────────────────────────────────────────────────────────

def run_vision_agent(image_path: str | Path) -> VisionResult:
    """
    Entry point for Agent 1.

    Parameters
    ----------
    image_path : path to a PNG / JPG bill image (or .txt for tests)

    Returns
    -------
    VisionResult with extracted bill JSON + confidence metadata
    """
    image_path = Path(image_path)

    # Try GPT-4o vision first (only for real image files)
    if image_path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        raw = _llm_vision_extract(image_path)
        if raw:
            extracted = _normalise_llm_output(raw, ocr_confidence=0.97)
            return VisionResult(
                extracted=extracted,
                ocr_confidence=0.97,
                extraction_method="llm_vision",
            )

    # Rule-based fallback for any file type
    extracted, confidence = _rule_based_extract(image_path)
    extracted["extraction_method"] = "rule_based"
    return VisionResult(
        extracted=extracted,
        ocr_confidence=confidence,
        extraction_method="rule_based",
    )

