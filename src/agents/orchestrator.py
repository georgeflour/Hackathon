"""
agents/orchestrator.py  —  Pipeline Orchestrator
-------------------------------------------------
Chains the three agents end-to-end:
  Image  ->  VisionAgent  ->  MatcherAgent  ->  ReplyAgent  ->  FinalAnswer
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from typing import Any
from src.agents.vision_agent  import run_vision_agent,  VisionResult
from src.agents.matcher_agent import run_matcher_agent, MatcherResult
from src.agents.reply_agent   import run_reply_agent,   ReplyResult
def run_pipeline(
    image_path: str | Path,
    question: str,
    extra_passages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Full end-to-end pipeline.
    Returns a single result dict containing:
      - answer, citations, confidence (top-level for easy access)
      - agent1_vision  : extraction output
      - agent2_matcher : match result + DWH context
      - agent3_reply   : retrieved passages used
    """
    # Agent 1
    vision: VisionResult = run_vision_agent(image_path)
    # Agent 2
    matcher: MatcherResult = run_matcher_agent(vision.extracted)
    matcher_dict = asdict(matcher)
    # Agent 3
    reply: ReplyResult = run_reply_agent(
        question=question,
        vision_result=vision.extracted,
        matcher_result=matcher_dict,
        extra_passages=extra_passages,
    )
    return {
        "answer":             reply.answer_text,
        "citations":          reply.citations,
        "confidence_label":   reply.confidence_label,
        "confidence_score":   reply.confidence_score,
        "unsupported_claims": reply.unsupported_claims,
        "prompt_package_id":  reply.prompt_package_id,
        "agent1_vision": {
            "extracted":         vision.extracted,
            "ocr_confidence":    vision.ocr_confidence,
            "extraction_method": vision.extraction_method,
        },
        "agent2_matcher": matcher_dict,
        "agent3_reply": {
            "retrieved_passages": reply.retrieved_passages,
        },
    }
