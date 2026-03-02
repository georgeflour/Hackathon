# Hackathon: Hack to the Future

## Challenge

**Image → Extract → Matching with DWH → RAG → Answer with citations + confidence**

### Requirements

- **Multimodal vision model** για extraction πληροφοριών από εικόνα bill (PNG/JPG)
- **Structured data extraction** σε machine-readable format (JSON/XML) με entities:  
  `customer ID`, `billing period`, `line items`, `consumption`, `tariff`
- **Matching engine** για σύνδεση extracted IDs με DWH tables:  
  `Billing_Header`, `Billing_Lines`, `Customer_Context`
- Χειρισμός cases: **1 match / κανένα match**
- **RAG pipeline** με retrieval queries, metadata filters και knowledge corpus (FAQs, policies, regulated charges)
- **Confidence scoring** σε κάθε στάδιο (extraction, matching, retrieval, answer)
- **Citation mechanism** — κάθε απάντηση να references συγκεκριμένα documents
- **Hallucination prevention**: το LLM να απαντά ΜΟΝΟ βάσει retrieved context
- **Modular αρχιτεκτονική** — κάθε step ανεξάρτητο component
- **API ή application interface** για demo

---

## Δυνατότητες της Εφαρμογής

- Upload εικόνας λογαριασμού και αυτόματη ανάλυσή της
- Εμφάνιση structured summary των extracted δεδομένων
- Αυτόματη αναγνώριση και σύνδεση με το προφίλ πελάτη από το DWH
- Εξήγηση ανάλυσης χρεώσεων (energy / regulated / taxes)
- Σύγκριση τρέχοντος λογαριασμού με ιστορικό (avg 6 μηνών, last 3 bills)
- Εντοπισμός λόγων αύξησης λογαριασμού
- Grounded απαντήσεις με citations από knowledge base
- Clarifying questions όταν υπάρχει αμφιβολία ή ελλιπή στοιχεία
- Υποστήριξη για **residential** και **business** segment

### Bonus

- Multi-query retrieval και re-ranking αποτελεσμάτων
- Explainability UI — εμφάνιση γιατί έγινε κάθε retrieval decision
- Hallucination detection flag στην απάντηση

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python 3.11+) |
| Frontend | Next.js 14 — TypeScript + Tailwind CSS |
| LLM / Vision | OpenAI GPT-4o (set `OPENAI_API_KEY`) |
| OCR fallback | Tesseract + rule-based regex parser |
| Fuzzy matching | rapidfuzz |
| Retrieval (MVP) | BM25 keyword over `data/knowledge/` |
| Retrieval (stretch) | FAISS + sentence-transformers |
| Mock DWH | CSV files in `data/dwh/` |

---

## Three-Agent Pipeline

```
Bill Image (JPG/PNG)
       │
       ▼
┌──────────────────────┐
│  Agent 1             │  ← src/agents/vision_agent.py
│  VisionAgent         │    GPT-4o vision OR Tesseract + regex
│  Extracts bill JSON  │
└──────────────────────┘
       │  ExtractedBill JSON
       ▼
┌──────────────────────┐
│  Agent 2             │  ← src/agents/matcher_agent.py
│  MatcherAgent        │    Exact account → meter → fuzzy name/addr
│  DWH lookup          │    Returns CustomerContext + BillingHistory
└──────────────────────┘
       │  MatchResult JSON
       ▼
┌──────────────────────┐
│  Agent 3             │  ← src/agents/reply_agent.py
│  ReplyAgent          │    Multi-query retrieval → prompt package
│  Grounded answer     │    → LLM (temp=0) → post-verifier
└──────────────────────┘
       │
       ▼
  Cited answer + confidence score
```

Orchestrator: `src/agents/orchestrator.py` — chains all three.

---

## Repository Layout

```
Hackathon/
├── README.md                        ← you are here
├── requirements.txt
├── pytest.ini
├── .gitignore
│
├── schemas/                         ← JSON schemas (DWH tables + extracted bill)
│   ├── billing_header.json
│   ├── billing_lines.json
│   ├── customer_context.json
│   └── extracted_bill_example.json
│
├── data/
│   ├── dwh/                         ← mock DWH CSVs  (README: data/dwh/README.md)
│   ├── knowledge/                   ← RAG corpus JSONs (README: data/knowledge/README.md)
│   ├── samples/                     ← bill images (git-ignored)
│   └── extracted/                   ← extracted JSONs (git-ignored)
│
├── src/
│   ├── agents/                      ← README: src/agents/README.md  ★ START HERE
│   │   ├── vision_agent.py          ← Agent 1
│   │   ├── matcher_agent.py         ← Agent 2
│   │   ├── reply_agent.py           ← Agent 3
│   │   └── orchestrator.py          ← pipeline glue
│   │
│   ├── extractor/                   ← README: src/extractor/README.md
│   │   ├── ocr.py                   ← Tesseract wrapper
│   │   └── parser.py                ← rule-based field extractor
│   │
│   ├── matcher/                     ← README: src/matcher/README.md
│   │   └── match_service.py         ← exact + fuzzy matching logic
│   │
│   ├── retriever/                   ← README: src/retriever/README.md
│   │   └── retriever.py             ← BM25 knowledge retriever
│   │
│   ├── rag/                         ← README: src/rag/README.md
│   │   ├── prompt_package.py        ← builds the RAG prompt JSON
│   │   └── llm_runner.py            ← calls OpenAI / stub
│   │
│   └── backend/                     ← README: src/backend/README.md
│       └── app/
│           └── main.py              ← FastAPI app
│
└── ui/                              ← README: ui/README.md
    └── src/
        ├── app/                     ← Next.js App Router pages
        ├── components/              ← UploadForm, ExtractedPreview, MatchPanel, AnswerPanel
        └── lib/
            └── api.ts               ← typed fetch wrappers
```

---

## Build Order — follow these READMEs in sequence

| Step | README | What gets built |
|------|--------|-----------------|
| 0 | `data/dwh/README.md` | Mock DWH CSV data |
| 1 | `data/knowledge/README.md` | RAG knowledge corpus |
| 2 | `src/extractor/README.md` | OCR wrapper + rule-based parser |
| 3 | `src/matcher/README.md` | Exact + fuzzy customer matching |
| 4 | `src/retriever/README.md` | BM25 knowledge retriever |
| 5 | `src/rag/README.md` | Prompt package + LLM runner |
| 6 | `src/agents/README.md` | Three agents + orchestrator |
| 7 | `src/backend/README.md` | FastAPI endpoints |
| 8 | `ui/README.md` | Next.js frontend |

---

## Quickstart (after all steps are complete)

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...          # optional — stub works without it
uvicorn src.backend.app.main:app --reload --port 8000

# Frontend (separate terminal)
cd ui && npm install && npm run dev   # → http://localhost:3000

# Tests
source .venv/bin/activate
python -m pytest src -v
```

API docs: http://localhost:8000/docs

---

## Environment Variables

`src/backend/.env` (create manually, never commit):
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

`ui/.env.local` (already present):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
