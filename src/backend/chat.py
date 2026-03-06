from fastapi import APIRouter
from pydantic import BaseModel
import asyncio

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    rag_context: str = ""
    sql_context: str = ""

@router.post("/chat")
async def chat(req: ChatRequest):
    # Simulate a small network delay
    await asyncio.sleep(1.5)
    
    # Check what kind of data came through
    has_sql = bool(req.sql_context)
    has_rag = bool(req.rag_context)
    
    mock_reply = (
        f"✅ **Mock Backend Response Successful**!\n\n"
        f"Το ερώτημα που έφτασε στο Backend ήταν:\n"
        f"> *\"{req.question}\"*\n\n"
        f"**Συνοδευτικά δεδομένα**:\n"
        f"- SQL Context Present: {'Ναι' if has_sql else 'Όχι'}\n"
        f"- RAG Context Present: {'Ναι' if has_rag else 'Όχι'}\n"
    )

    return {"answer": mock_reply}