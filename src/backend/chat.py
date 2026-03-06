from fastapi import APIRouter
from pydantic import BaseModel
from src.backend.agent import ask_agent

router = APIRouter()

SYSTEM_PROMPT = """
Είσαι βοηθός εξυπηρέτησης πελατών λογαριασμών ενέργειας.
Απαντάς πάντα στα ελληνικά.
Χρησιμοποιείς μόνο τα παρεχόμενα facts από SQL και RAG.
Αν δεν υπάρχουν αρκετά στοιχεία, το λες καθαρά.
Δεν επινοείς αριθμούς, χρεώσεις, ημερομηνίες ή πολιτικές.
"""

class ChatRequest(BaseModel):
    question: str
    rag_context: str = ""
    sql_context: str = ""

@router.post("/chat")
def chat(req: ChatRequest):
    user_prompt = f"""
    Ερώτηση χρήστη:
    {req.question}
    
    Δεδομένα από SQL:
    {req.sql_context if req.sql_context else "Δεν υπάρχουν."}
    
    Δεδομένα από knowledge base:
    {req.rag_context if req.rag_context else "Δεν υπάρχουν."}
    
    Οδηγίες:
    - Απάντησε στα ελληνικά.
    - Αν τα δεδομένα δεν αρκούν, ζήτησε διευκρίνιση.
    - Μη χρησιμοποιήσεις εξωτερική γνώση.
    - Δώσε σύντομη, σαφή απάντηση.
    """

    answer = ask_agent(user_prompt)
    return {"answer": answer.strip()}
