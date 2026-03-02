"""
rag/llm_runner.py
-----------------
Calls the LLM with a prompt package and returns a structured LlmAnswer.

Two modes:
  REAL  — OPENAI_API_KEY is set → calls GPT-4o at temperature=0
  STUB  — no API key → returns a templated answer from the retrieved passages
          (lets the full pipeline run and be tested without spending tokens)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any


# ─── result type ─────────────────────────────────────────────────────────────

@dataclass
class LlmAnswer:
    answer_text: str
    citations: list[dict[str, Any]]        # [{"doc_id": str, "page": int, "snippet": str}]
    confidence_label: str                  # "High" | "Medium" | "Low"
    confidence_score: float                # 0.0 – 1.0
    unsupported_claims: list[str] = field(default_factory=list)   # filled by ReplyAgent


# ─── confidence calibration ───────────────────────────────────────────────────

def _confidence_from_passages(passages: list[dict[str, Any]]) -> tuple[float, str]:
    """
    Estimate answer confidence from the average retrieval score of the
    passages that were used to answer.

    Returns (score, label) where label is "High" | "Medium" | "Low".
    """
    if not passages:
        return 0.4, "Low"
    avg = sum(p.get("final_score", 0.7) for p in passages) / len(passages)
    avg = min(max(avg, 0.0), 1.0)
    if avg >= 0.85:
        label = "High"
    elif avg >= 0.65:
        label = "Medium"
    else:
        label = "Low"
    return round(avg, 3), label


# ─── prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(package: dict[str, Any]) -> str:
    """
    Render the prompt package as a plain-text string for the chat API.
    The structure mirrors what a human reviewer would want to see.
    """
    sys_instr  = package.get("system_instructions", "")
    summary    = package.get("extracted_bill_summary", {})
    passages   = package.get("retrieved_passages", [])
    question   = package.get("user_question", "")
    customer   = package.get("matched_customer", {})
    ctx        = summary.get("customer_context", {})
    history    = summary.get("billing_history", [])

    # ── bill summary block ────────────────────────────────────────────────────
    period     = summary.get("service_period", {})
    total      = summary.get("total_due", {})
    lines      = summary.get("line_items", [])
    line_str   = "\n".join(
        f"  - {li.get('description','?')}: "
        f"{li.get('quantity_kwh','') or ''} kWh  "
        f"amount={li.get('amount','?')}"
        for li in lines
    ) or "  (none extracted)"

    # ── customer context block ────────────────────────────────────────────────
    ctx_str = ""
    if ctx:
        ctx_str = (
            f"\n--- CUSTOMER CONTEXT ---\n"
            f"Name        : {ctx.get('customer_name', 'unknown')}\n"
            f"Segment     : {ctx.get('segment', 'unknown')}\n"
            f"Tariff      : {ctx.get('active_tariff', 'unknown')}\n"
            f"Avg kWh/6m  : {ctx.get('avg_kwh_6m', 'N/A')}\n"
            f"Last 3 bills: {ctx.get('last_3_bills_total', 'N/A')} EUR"
        )

    history_str = ""
    if history:
        rows = "\n".join(
            f"  {b.get('billing_id','?')}  {b.get('period_from','?')}→{b.get('period_to','?')}  "
            f"{b.get('total_amount','?')} EUR"
            for b in history[:5]
        )
        history_str = f"\n--- BILLING HISTORY (last {len(history[:5])} bills) ---\n{rows}"

    # ── passages block ────────────────────────────────────────────────────────
    passages_str = ""
    for i, p in enumerate(passages, 1):
        passages_str += (
            f"\n[{i}] Source: {p.get('doc_id','?')}, page {p.get('page',1)}\n"
            f"Title: {p.get('doc_title','')}\n"
            f"{p.get('text_snippet','')}\n"
        )

    return (
        f"{sys_instr}\n\n"
        f"--- BILL SUMMARY ---\n"
        f"Bill number : {summary.get('bill_number','unknown')}\n"
        f"Account     : {summary.get('account_number','unknown')}\n"
        f"Period      : {period.get('start','?')} → {period.get('end','?')}\n"
        f"Total due   : {total.get('value','?')} {total.get('currency','EUR')}\n"
        f"Tariff      : {summary.get('tariff_code','unknown')}\n"
        f"Line items  :\n{line_str}"
        f"{ctx_str}"
        f"{history_str}\n\n"
        f"--- RETRIEVED PASSAGES ---{passages_str}\n"
        f"--- CUSTOMER QUESTION ---\n{question}\n\n"
        f"Answer (use only the passages above, cite each fact):"
    )


# ─── citation extractor ───────────────────────────────────────────────────────

def _extract_citations(
    answer_text: str,
    passages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Parse inline citations of the form (Source: faq-001, page 1) from the
    answer text and cross-reference against the actual passages used.
    Falls back to returning all passages as citations when none are found inline.
    """
    pattern = r"\(Source:\s*([\w\-]+),\s*page\s*(\d+)\)"
    found   = re.findall(pattern, answer_text, re.IGNORECASE)

    if found:
        seen: set[str] = set()
        citations = []
        for doc_id, page in found:
            key = f"{doc_id}-{page}"
            if key in seen:
                continue
            seen.add(key)
            # Find matching passage for the snippet
            snippet = next(
                (p.get("text_snippet", "")[:80] for p in passages if p.get("doc_id") == doc_id),
                "",
            )
            citations.append({"doc_id": doc_id, "page": int(page), "snippet": snippet})
        return citations

    # Fallback: cite top-3 passages
    return [
        {
            "doc_id":  p.get("doc_id", "unknown"),
            "page":    p.get("page", 1),
            "snippet": p.get("text_snippet", "")[:80],
        }
        for p in passages[:3]
    ]


# ─── stub mode ────────────────────────────────────────────────────────────────

def _stub_answer(package: dict[str, Any]) -> LlmAnswer:
    """
    Generate a templated answer from the retrieved passages without calling
    any external API. Used when OPENAI_API_KEY is not set.
    """
    passages   = package.get("retrieved_passages", [])
    summary    = package.get("extracted_bill_summary", {})
    question   = package.get("user_question", "")
    period     = summary.get("service_period", {})
    total      = summary.get("total_due", {})
    ctx        = summary.get("customer_context", {})
    history    = summary.get("billing_history", [])

    conf_score, conf_label = _confidence_from_passages(passages)

    # Build a passage-grounded narrative
    passage_snippets = "\n".join(
        f"• ({p.get('doc_id','?')}, p{p.get('page',1)}): {p.get('text_snippet','')[:200]}"
        for p in passages[:4]
    )

    # Personalised comparison if billing history is available
    history_note = ""
    if len(history) >= 2:
        prev = history[1] if isinstance(history[1], dict) else {}
        prev_total = prev.get("total_amount", "N/A")
        history_note = (
            f"\n\nCompared to your previous bill of {prev_total} EUR, "
            f"your current bill of {total.get('value','?')} EUR "
            f"{'is higher' if str(total.get('value','0')) > str(prev_total) else 'has changed'}."
        )

    avg_kwh = ctx.get("avg_kwh_6m")
    consumption_note = ""
    if avg_kwh:
        consumption_note = (
            f" Your 6-month average consumption is {avg_kwh} kWh/month, "
            "which provides useful context for this period."
        )

    answer = (
        f"[STUB MODE — connect OPENAI_API_KEY for a real LLM answer]\n\n"
        f"Regarding your question: \"{question}\"\n\n"
        f"Your bill for the period {period.get('start','?')} → {period.get('end','?')} "
        f"totals {total.get('value','?')} {total.get('currency','EUR')}."
        f"{history_note}{consumption_note}\n\n"
        f"Based on the retrieved knowledge documents:\n{passage_snippets}\n\n"
        f"For a full explanation, the above documents cover the main reasons for "
        f"bill changes, regulated charges, and tariff details. "
        f"Please review each cited document for details. "
        f"(Source: {passages[0]['doc_id'] if passages else 'N/A'}, "
        f"page {passages[0]['page'] if passages else 1})"
    )

    citations = _extract_citations(answer, passages)
    return LlmAnswer(
        answer_text=answer,
        citations=citations,
        confidence_label=conf_label,
        confidence_score=conf_score,
    )


# ─── real OpenAI call ────────────────────────────────────────────────────────

def _openai_answer(package: dict[str, Any]) -> LlmAnswer:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model  = os.getenv("OPENAI_MODEL", "gpt-4o")

    prompt   = _build_prompt(package)
    passages = package.get("retrieved_passages", [])

    response = client.chat.completions.create(
        model=model,
        temperature=package.get("generation_parameters", {}).get("temperature", 0.0),
        max_tokens=package.get("generation_parameters", {}).get("max_tokens", 1024),
        messages=[
            {"role": "system", "content": package.get("system_instructions", "")},
            {"role": "user",   "content": prompt},
        ],
    )

    answer_text = response.choices[0].message.content or ""
    conf_score, conf_label = _confidence_from_passages(passages)
    citations = _extract_citations(answer_text, passages)

    return LlmAnswer(
        answer_text=answer_text,
        citations=citations,
        confidence_label=conf_label,
        confidence_score=conf_score,
    )


# ─── public interface ────────────────────────────────────────────────────────

def run_llm(package: dict[str, Any]) -> LlmAnswer:
    """
    Call the LLM with a prompt package.

    Uses real OpenAI when OPENAI_API_KEY is set, otherwise falls back
    to stub mode so the full pipeline can run without an API key.
    """
    if os.getenv("OPENAI_API_KEY"):
        return _openai_answer(package)
    return _stub_answer(package)

