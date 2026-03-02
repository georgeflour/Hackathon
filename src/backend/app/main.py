"""
backend/app/main.py
-------------------
FastAPI application — exposes the three-agent pipeline as an HTTP API.
Endpoints
---------
  GET  /health
  POST /upload        → Agent 1 (VisionAgent)
  GET  /extracted/{id}
  POST /match         → Agent 2 (MatcherAgent)
  POST /explain       → Agent 3 (ReplyAgent)
  POST /pipeline      → All three agents chained
"""
from __future__ import annotations
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# Load .env next to this file (OPENAI_API_KEY, OPENAI_MODEL, …)
load_dotenv(Path(__file__).parent / ".env")
from src.agents.vision_agent  import run_vision_agent
from src.agents.matcher_agent import run_matcher_agent
from src.agents.reply_agent   import run_reply_agent
from src.agents.orchestrator  import run_pipeline
# ─── paths ────────────────────────────────────────────────────────────────────
DATA_DIR      = Path(__file__).parent.parent.parent.parent / "data"
SAMPLES_DIR   = DATA_DIR / "samples"
EXTRACTED_DIR = DATA_DIR / "extracted"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
# ─── app ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Billing RAG API — Three-Agent Pipeline",
    version="0.2.0",
    description=(
        "Vision-to-RAG pipeline: upload a bill image → extract → match customer "
        "→ retrieve knowledge → grounded answer with citations."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─── request models ───────────────────────────────────────────────────────────
class MatchRequest(BaseModel):
    extracted: dict
class ExplainRequest(BaseModel):
    extracted: dict
    match_result: dict
    question: str
    retrieved_passages: list[dict] = []
class PipelineRequest(BaseModel):
    extracted_id: str
    question: str = "Why is my bill higher this month?"
# ─── endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
@app.post("/upload")
async def upload(file: UploadFile):
    """
    Agent 1 — VisionAgent.
    Upload a bill image → extract structured JSON.
    """
    suffix   = Path(file.filename or "bill.jpg").suffix
    filename = f"{uuid.uuid4()}{suffix}"
    saved    = SAMPLES_DIR / filename
    content = await file.read()
    saved.write_bytes(content)
    vision = run_vision_agent(saved)
    extracted = vision.extracted
    # Annotate with source document info
    extracted["source_document"] = {
        "file_name": file.filename,
        "uri":       str(saved),
        "mime_type": file.content_type or "application/octet-stream",
    }
    # Persist extracted JSON for later /pipeline calls
    extracted_id   = extracted.get("extracted_id", str(uuid.uuid4()))
    extracted_file = EXTRACTED_DIR / f"{extracted_id}.json"
    extracted_file.write_text(json.dumps(extracted, indent=2))
    return {
        **extracted,
        "ocr_confidence":    vision.ocr_confidence,
        "extraction_method": vision.extraction_method,
        "agent":             vision.agent_name,
    }
@app.get("/extracted/{extracted_id}")
def get_extracted(extracted_id: str):
    """Return a previously extracted bill JSON by ID."""
    path = EXTRACTED_DIR / f"{extracted_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Extracted bill '{extracted_id}' not found.")
    return json.loads(path.read_text())
@app.post("/match")
def match(req: MatchRequest):
    """
    Agent 2 — MatcherAgent.
    Match extracted bill to DWH customer + enrich with billing history.
    """
    result = run_matcher_agent(req.extracted)
    return {**asdict(result), "agent": result.agent_name}
@app.post("/explain")
def explain(req: ExplainRequest):
    """
    Agent 3 — ReplyAgent.
    Multi-query retrieval → prompt package → LLM → grounded answer.
    """
    result = run_reply_agent(
        question=req.question,
        vision_result=req.extracted,
        matcher_result=req.match_result,
        extra_passages=req.retrieved_passages or None,
    )
    return {
        "answer":             result.answer_text,
        "citations":          result.citations,
        "confidence_label":   result.confidence_label,
        "confidence_score":   result.confidence_score,
        "unsupported_claims": result.unsupported_claims,
        "prompt_package_id":  result.prompt_package_id,
        "retrieved_passages": result.retrieved_passages,
        "agent":              result.agent_name,
    }
@app.post("/pipeline")
def pipeline(req: PipelineRequest):
    """
    Full pipeline — all three agents chained.
    Loads the stored extracted JSON then runs MatcherAgent + ReplyAgent.
    If the original image is still on disk, it is NOT re-processed (use /upload for that).
    """
    path = EXTRACTED_DIR / f"{req.extracted_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Extracted bill '{req.extracted_id}' not found.")
    extracted = json.loads(path.read_text())
    # Run Agents 2 & 3 (VisionAgent already ran at /upload time)
    matcher = run_matcher_agent(extracted)
    matcher_dict = asdict(matcher)
    reply = run_reply_agent(
        question=req.question,
        vision_result=extracted,
        matcher_result=matcher_dict,
    )
    return {
        "answer":             reply.answer_text,
        "citations":          reply.citations,
        "confidence_label":   reply.confidence_label,
        "confidence_score":   reply.confidence_score,
        "unsupported_claims": reply.unsupported_claims,
        "prompt_package_id":  reply.prompt_package_id,
        "agent1_vision":  {"extracted": extracted, "extraction_method": extracted.get("extraction_method")},
        "agent2_matcher": matcher_dict,
        "agent3_reply":   {"retrieved_passages": reply.retrieved_passages},
    }
