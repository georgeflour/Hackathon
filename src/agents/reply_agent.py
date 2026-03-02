"""
agents/reply_agent.py  —  Agent 3: Grounded Reply / RAG Agent
--------------------------------------------------------------
Multi-query retrieval → prompt package → LLM → post-generation verifier → ReplyResult
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.retriever.retriever import retrieve
from src.rag.prompt_package import build_prompt_package
from src.rag.llm_runner import run_llm, LlmAnswer


# ─── result type ─────────────────────────────────────────────────────────────

@dataclass
class ReplyResult:
    answer_text: str
    citations: list[dict[str, Any]]
    confidence_label: str                        # High | Medium | Low
    confidence_score: float                      # 0.0 – 1.0
    unsupported_claims: list[str] = field(default_factory=list)
    prompt_package_id: str = ""
    retrieved_passages: list[dict[str, Any]] = field(default_factory=list)
    agent_name: str = "ReplyAgent"


# ─── multi-query builder ──────────────────────────────────────────────────────

def _build_queries(
    question: str,
    extracted: dict[str, Any],
    matcher: dict[str, Any],
) -> list[str]:
    """
    Build 3 complementary retrieval queries to maximise recall across
    the knowledge corpus:
      Q1 — semantic (personalised with bill context)
      Q2 — tariff / charge focused
      Q3 — policy / dispute focused
    """
    acct    = (extracted.get("account_number") or {}).get("normalized", "")
    tariff  = extracted.get("tariff_code") or ""
    period  = extracted.get("service_period") or {}
    total   = (extracted.get("total_due") or {}).get("value", "")
    segment = (matcher.get("customer_context") or {}).get("segment", "")

    q1 = (
        f"{question} account {acct} "
        f"period {period.get('start','')} {period.get('end','')} "
        f"total {total} {segment}"
    )
    q2 = f"tariff {tariff} energy charge regulated charges kWh consumption increase network fees"
    q3 = "billing policy regulated charges dispute VAT network charge explanation invoice"

    return [q1, q2, q3]


# ─── claim verifier ───────────────────────────────────────────────────────────

def _verify_claims(
    answer_text: str,
    passages: list[dict[str, Any]],
) -> list[str]:
    """
    Lightweight post-generation verifier.
    Flags sentences that contain numeric values not found in any passage.
    """
    corpus = " ".join(p.get("text_snippet", "") for p in passages).lower()
    unsupported: list[str] = []

    for sent in re.split(r"[.!?\n]", answer_text):
        sent = sent.strip()
        if not sent or not re.search(r"\d", sent):
            continue
        # Extract numbers from this sentence
        nums = re.findall(r"\d[\d.,]*", sent)
        # Check if at least one number appears somewhere in the passage corpus
        if not any(n.replace(",", ".") in corpus for n in nums):
            unsupported.append(sent[:150])

    return unsupported


# ─── public interface ─────────────────────────────────────────────────────────

def run_reply_agent(
    question: str,
    vision_result: dict[str, Any],
    matcher_result: dict[str, Any],
    extra_passages: list[dict[str, Any]] | None = None,
) -> ReplyResult:
    """
    Entry point for Agent 3.

    Parameters
    ----------
    question       : customer's free-text question
    vision_result  : VisionResult.extracted dict
    matcher_result : MatcherResult serialised as dict
    extra_passages : optional pre-retrieved passages (e.g. from API caller)
    """
    customer_id = matcher_result.get("matched_customer_id")

    # ── 1. Multi-query retrieval ──────────────────────────────────────────────
    queries  = _build_queries(question, vision_result, matcher_result)
    passages: list[dict[str, Any]] = list(extra_passages or [])
    seen_ids: set[str] = {p.get("passage_id", "") for p in passages}

    for q in queries:
        for p in retrieve(query=q, customer_id=customer_id, top_k=3):
            pid = p.get("passage_id", "")
            if pid not in seen_ids:
                passages.append(p)
                seen_ids.add(pid)

    # Sort by relevance, keep top 6
    passages.sort(key=lambda p: p.get("final_score", 0), reverse=True)
    passages = passages[:6]

    # ── 2. Enrich extracted bill with customer context ────────────────────────
    enriched = {
        **vision_result,
        "customer_context": matcher_result.get("customer_context", {}),
        "billing_history":  matcher_result.get("billing_history", []),
    }

    # ── 3. Build prompt package ───────────────────────────────────────────────
    package = build_prompt_package(
        user_question=question,
        extracted_bill=enriched,
        match_result=matcher_result,
        retrieved_passages=passages,
    )

    # ── 4. LLM call ───────────────────────────────────────────────────────────
    llm: LlmAnswer = run_llm(package)

    # ── 5. Post-generation claim verification ─────────────────────────────────
    unsupported = _verify_claims(llm.answer_text, passages)
    answer_text = llm.answer_text
    if unsupported:
        caveat = (
            "\n\n⚠️ Note: the following claims could not be verified "
            "against retrieved documents and may require manual review:\n- "
            + "\n- ".join(unsupported)
        )
        answer_text += caveat

    return ReplyResult(
        answer_text=answer_text,
        citations=llm.citations,
        confidence_label=llm.confidence_label,
        confidence_score=llm.confidence_score,
        unsupported_claims=unsupported,
        prompt_package_id=package["package_id"],
        retrieved_passages=passages,
    )

