"""
matcher/match_service.py
------------------------
Matches an ExtractedBill dict against Customer_Context.csv (mock DWH).

Matching strategy (highest confidence first):
  1. Exact account number          → score 0.99
  2. Exact meter ID overlap        → score 0.97
  3. Exact normalised name+address → score 0.95
  4. Fuzzy name + address          → graduated score
       ≥ 0.90  fuzzy_high     (single top match)
       0.75–0.90 fuzzy_ambiguous (top-3 + clarifying question)
       < 0.75  none

Returns a MatchResult dataclass.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

# ─── default CSV path ─────────────────────────────────────────────────────────
_DEFAULT_CSV = (
    Path(__file__).parent.parent.parent / "data" / "dwh" / "Customer_Context.csv"
)


# ─── result types ─────────────────────────────────────────────────────────────

@dataclass
class Candidate:
    customer_id: str
    customer_name: str
    score: float        # 0.0 – 1.0
    match_field: str    # which field drove the match


@dataclass
class MatchResult:
    match_type: str                        # exact|fuzzy_high|fuzzy_ambiguous|none
    matched_customer_id: str | None
    score: float
    candidates: list[Candidate] = field(default_factory=list)
    clarifying_question: str | None = None


# ─── normalisation helpers ────────────────────────────────────────────────────

def _norm_digits(value: Any) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower().strip())


# ─── DWH loader ───────────────────────────────────────────────────────────────

def _load_customers(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str)
    df["_account_norm"]  = df["account_numbers"].apply(_norm_digits)
    df["_primary_norm"]  = df["primary_account"].apply(_norm_digits)
    df["_name_norm"]     = df["customer_name"].apply(_norm)
    df["_addr_norm"]     = df["addresses"].apply(_norm)
    df["_meters_raw"]    = df["service_meters"].astype(str)
    return df


# ─── clarifying question builder ─────────────────────────────────────────────

def _make_clarifying_question(
    candidates: list[Candidate], df: pd.DataFrame
) -> str:
    addr_map = df.set_index("customer_id")["addresses"].to_dict()
    lines = []
    for i, c in enumerate(candidates):
        letter = chr(65 + i)           # A, B, C
        addr = addr_map.get(c.customer_id, "unknown address")
        lines.append(f"  {letter}) {c.customer_name} — {addr}")
    lines.append("  D) None of these")
    options = "\n".join(lines)
    return (
        "We found multiple possible matches for this bill. "
        "Which customer does this bill belong to?\n" + options
    )


# ─── public interface ─────────────────────────────────────────────────────────

def match_customer(
    extracted: dict[str, Any],
    csv_path: Path = _DEFAULT_CSV,
) -> MatchResult:
    """
    Match an extracted bill dict to a customer in the DWH CSV.

    Parameters
    ----------
    extracted : ExtractedBill dict (output of extractor.parser.extract_fields)
    csv_path  : path to Customer_Context.csv

    Returns
    -------
    MatchResult with match_type, matched_customer_id, score, candidates,
    and an optional clarifying_question.
    """
    df = _load_customers(csv_path)

    # Pull identifiers from extracted dict (handle missing keys gracefully)
    acct_norm   = _norm_digits((extracted.get("account_number") or {}).get("normalized")
                               or (extracted.get("account_number") or {}).get("value"))
    name_norm   = _norm((extracted.get("customer_name") or {}).get("normalized"))
    addr_norm   = _norm(" ".join(extracted.get("customer_address") or []))
    meter_ids   = [m.strip() for m in (extracted.get("meter_ids") or []) if m.strip()]

    # ── Step 2: Exact account number ─────────────────────────────────────────
    if acct_norm:
        for _, row in df.iterrows():
            if acct_norm in (row["_account_norm"], row["_primary_norm"]):
                cand = Candidate(
                    customer_id=str(row["customer_id"]),
                    customer_name=str(row["customer_name"]),
                    score=0.99,
                    match_field="account_number",
                )
                return MatchResult(
                    match_type="exact",
                    matched_customer_id=str(row["customer_id"]),
                    score=0.99,
                    candidates=[cand],
                )

    # ── Step 3: Exact meter ID overlap ───────────────────────────────────────
    if meter_ids:
        for _, row in df.iterrows():
            stored_meters = set(re.findall(r"[\w\-]+", row["_meters_raw"]))
            if set(meter_ids) & stored_meters:
                cand = Candidate(
                    customer_id=str(row["customer_id"]),
                    customer_name=str(row["customer_name"]),
                    score=0.97,
                    match_field="meter_id",
                )
                return MatchResult(
                    match_type="exact",
                    matched_customer_id=str(row["customer_id"]),
                    score=0.97,
                    candidates=[cand],
                )

    # ── Step 4: Exact normalised name + address ───────────────────────────────
    if name_norm:
        for _, row in df.iterrows():
            name_match = name_norm == row["_name_norm"]
            addr_match = (not addr_norm) or (addr_norm in row["_addr_norm"])
            if name_match and addr_match:
                cand = Candidate(
                    customer_id=str(row["customer_id"]),
                    customer_name=str(row["customer_name"]),
                    score=0.95,
                    match_field="name_address",
                )
                return MatchResult(
                    match_type="exact",
                    matched_customer_id=str(row["customer_id"]),
                    score=0.95,
                    candidates=[cand],
                )

    # ── Step 5: Fuzzy fallback ────────────────────────────────────────────────
    candidates: list[Candidate] = []
    for _, row in df.iterrows():
        name_score  = fuzz.token_set_ratio(name_norm, row["_name_norm"]) / 100
        addr_score  = fuzz.token_set_ratio(addr_norm, row["_addr_norm"]) / 100 if addr_norm else 0.0
        meter_score = 1.0 if (set(meter_ids) & set(re.findall(r"[\w\-]+", row["_meters_raw"]))) else 0.0
        final       = round(0.6 * name_score + 0.3 * addr_score + 0.1 * meter_score, 3)
        candidates.append(Candidate(
            customer_id=str(row["customer_id"]),
            customer_name=str(row["customer_name"]),
            score=final,
            match_field="fuzzy",
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    top = candidates[0] if candidates else None

    if not top or top.score < 0.75:
        return MatchResult(match_type="none", matched_customer_id=None, score=0.0)

    if top.score >= 0.90:
        return MatchResult(
            match_type="fuzzy_high",
            matched_customer_id=top.customer_id,
            score=top.score,
            candidates=candidates[:3],
        )

    # Ambiguous: top candidates within 15 % of the top score
    top3 = [c for c in candidates if c.score >= top.score - 0.15][:3]
    return MatchResult(
        match_type="fuzzy_ambiguous",
        matched_customer_id=None,
        score=top.score,
        candidates=top3,
        clarifying_question=_make_clarifying_question(top3, df),
    )

