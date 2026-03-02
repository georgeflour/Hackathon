"""
rag/prompt_package.py
---------------------
Assembles all context into a single structured JSON package that is
passed to the LLM. Every field is intentional:

  system_instructions   → grounding & citation policy for the LLM
  extracted_bill_summary → personalised bill context
  matched_customer       → DWH customer + billing history
  retrieved_passages     → the only facts the LLM may cite
  citation_policy        → explicit rules shown to the LLM
  hallucination_policy   → what to do with unsupported claims
  generation_parameters  → deterministic output (temperature=0)
  retrieval_queries      → audit trail of what was retrieved and why
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


# ─── grounding system prompt ──────────────────────────────────────────────────

SYSTEM_INSTRUCTIONS = """You are a helpful and precise energy billing assistant for a utility company.

STRICT RULES — you MUST follow all of them:
1. Answer ONLY using facts present in the RETRIEVED PASSAGES section below.
2. For every numeric value, tariff rate, date, or policy fact you state, include an inline citation in the format: (Source: {doc_id}, page {page}).
3. If a retrieved passage does not contain enough information to answer part of the question, say exactly: "I don't have enough information in the retrieved documents to answer this part."
4. NEVER speculate, infer, or use knowledge outside the retrieved passages.
5. NEVER hallucinate charges, rates, or customer data.
6. If the customer data shows a billing history, use it to personalise your comparison (e.g. this month vs last month).
7. Structure your answer clearly: start with a direct answer, then explain line by line if relevant.
8. Keep your answer concise and customer-friendly — avoid jargon where possible."""


# ─── public function ──────────────────────────────────────────────────────────

def build_prompt_package(
    user_question: str,
    extracted_bill: dict[str, Any],
    match_result: dict[str, Any],
    retrieved_passages: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a fully structured RAG prompt package.

    Parameters
    ----------
    user_question      : the customer's question (free text)
    extracted_bill     : ExtractedBill dict from VisionAgent / parser
    match_result       : MatcherResult dict from MatcherAgent
    retrieved_passages : list of passage dicts from the retriever

    Returns
    -------
    A prompt package dict ready to be passed to run_llm()
    """
    # ── pull key fields from extracted bill ───────────────────────────────────
    acct    = (extracted_bill.get("account_number") or {}).get("normalized") \
              or (extracted_bill.get("account_number") or {}).get("value") or "unknown"
    period  = extracted_bill.get("service_period") or {}
    start   = period.get("start") or "unknown"
    end     = period.get("end")   or "unknown"
    total   = extracted_bill.get("total_due") or {}

    bill_summary = {
        "bill_number":    (extracted_bill.get("bill_number") or {}).get("value"),
        "account_number": acct,
        "customer_name":  (extracted_bill.get("customer_name") or {}).get("value"),
        "service_period": {"start": start, "end": end},
        "total_due":      total,
        "line_items":     extracted_bill.get("line_items") or [],
        "meter_ids":      extracted_bill.get("meter_ids") or [],
        "tariff_code":    extracted_bill.get("tariff_code"),
        # Enriched DWH data (injected by ReplyAgent before calling this)
        "customer_context": extracted_bill.get("customer_context") or {},
        "billing_history":  extracted_bill.get("billing_history") or [],
    }

    # ── auto-build retrieval query audit trail ────────────────────────────────
    retrieval_queries = [
        {
            "type": "metadata",
            "query_text": (
                f"customer_id={match_result.get('matched_customer_id')} "
                f"account={acct} period={start} to {end}"
            ),
        },
        {
            "type": "semantic",
            "query_text": (
                f"{user_question} account {acct} billing period {start} {end}"
            ),
        },
    ]

    return {
        "package_id":            f"pkg-{uuid.uuid4()}",
        "created_at":            datetime.now(timezone.utc).isoformat(),
        "system_instructions":   SYSTEM_INSTRUCTIONS,
        "user_question":         user_question,
        "extracted_bill_summary": bill_summary,
        "matched_customer":      match_result,
        "retrieval_queries":     retrieval_queries,
        "retrieved_passages":    retrieved_passages,
        "citation_policy": {
            "format":                           "(Source: {doc_id}, page {page})",
            "max_citations":                    5,
            "require_citation_for_numeric_claims": True,
        },
        "hallucination_policy": {
            "disallow_external_facts":   True,
            "unsupported_claim_action":  "add_caveat",
        },
        "generation_parameters": {
            "temperature": 0.0,
            "max_tokens":  1024,
        },
    }

