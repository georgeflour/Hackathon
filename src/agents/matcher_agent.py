"""
agents/matcher_agent.py  —  Agent 2: Database Matcher
------------------------------------------------------
Runs match_customer() against the DWH, then enriches the result with
full customer context and billing history from SQLite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.matcher.match_service import match_customer
from src.db.dwh import query_customer_by_id, query_billing_history, query_billing_lines


# ─── result type ─────────────────────────────────────────────────────────────

@dataclass
class MatcherResult:
    match_type: str                        # exact|fuzzy_high|fuzzy_ambiguous|none
    matched_customer_id: str | None
    score: float
    candidates: list[dict[str, Any]] = field(default_factory=list)
    clarifying_question: str | None = None
    customer_context: dict[str, Any] = field(default_factory=dict)
    billing_history: list[dict[str, Any]] = field(default_factory=list)
    agent_name: str = "MatcherAgent"


# ─── public interface ─────────────────────────────────────────────────────────

def run_matcher_agent(extracted: dict[str, Any]) -> MatcherResult:
    """
    Entry point for Agent 2.

    Parameters
    ----------
    extracted : ExtractedBill dict from VisionAgent

    Returns
    -------
    MatcherResult — match decision + enriched DWH context
    """
    # ── Core matching logic ───────────────────────────────────────────────────
    match = match_customer(extracted)

    # ── Serialise Candidate dataclasses to plain dicts ────────────────────────
    candidates = [
        {
            "customer_id":   c.customer_id,
            "customer_name": c.customer_name,
            "score":         c.score,
            "match_field":   c.match_field,
        }
        for c in match.candidates
    ]

    # ── Enrich with DWH data via SQLite ──────────────────────────────────────
    customer_context: dict[str, Any] = {}
    billing_history:  list[dict[str, Any]] = []

    if match.matched_customer_id:
        ctx = query_customer_by_id(match.matched_customer_id)
        if ctx:
            customer_context = dict(ctx)

        bills = query_billing_history(match.matched_customer_id)
        # Attach line items to each bill for richer context
        for bill in bills:
            bill["line_items"] = query_billing_lines(bill["billing_id"])
        billing_history = bills

    return MatcherResult(
        match_type=match.match_type,
        matched_customer_id=match.matched_customer_id,
        score=match.score,
        candidates=candidates,
        clarifying_question=match.clarifying_question,
        customer_context=customer_context,
        billing_history=billing_history,
    )

