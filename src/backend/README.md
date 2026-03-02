# Step 7 — FastAPI Backend

Location: `src/backend/`

This module exposes the three-agent pipeline as an HTTP API. The Next.js frontend calls these endpoints.

---

## Files to create

| File | Purpose |
|---|---|
| `src/backend/__init__.py` | empty |
| `src/backend/app/__init__.py` | empty |
| `src/backend/app/main.py` | FastAPI app with all endpoints |
| `src/backend/tests/__init__.py` | empty |
| `src/backend/tests/test_main.py` | integration tests |

---

## `main.py`

### App setup

```python
app = FastAPI(
    title="Billing RAG API — Three-Agent Pipeline",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Load `.env` with `python-dotenv` at startup: `load_dotenv(Path(__file__).parent / ".env")`.

### Endpoints to implement

#### `GET /health`
Returns `{"status": "ok", "version": "0.2.0"}`.

#### `POST /upload` — Agent 1

- Accept `file: UploadFile`.
- Save to `data/samples/{uuid}_{filename}`.
- Call `run_vision_agent(saved_path)`.
- Add `source_document` dict to `vision.extracted`.
- Save extracted JSON to `data/extracted/{extracted_id}.json`.
- Return extracted dict + `ocr_confidence`, `extraction_method`, `agent` fields.

#### `GET /extracted/{extracted_id}`

- Load and return JSON from `data/extracted/{extracted_id}.json`.
- Return 404 if not found.

#### `POST /match` — Agent 2

Request body:
```json
{ "extracted": { ...ExtractedBill... } }
```
- Call `run_matcher_agent(req.extracted)`.
- Return `asdict(result)` + `"agent": "MatcherAgent"`.

#### `POST /explain` — Agent 3

Request body:
```json
{
  "extracted": {...},
  "match_result": {...},
  "question": "Why is my bill higher?",
  "retrieved_passages": []
}
```
- Call `run_reply_agent(question, extracted, match_result, extra_passages)`.
- Return answer, citations, confidence, unsupported_claims, prompt_package_id, retrieved_passages, agent.

#### `POST /pipeline` — All three agents

Request body:
```json
{ "extracted_id": "...", "question": "..." }
```
- Load extracted JSON from disk.
- If image file exists at `source_document.uri` → call `run_pipeline(image_path, question)`.
- If image not found → skip VisionAgent re-run, call MatcherAgent + ReplyAgent directly using the stored extracted JSON.
- Return full pipeline result dict.

### Pydantic request models

```python
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
```

### Data directory path

```python
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
```

---

## Running the server

```bash
source .venv/bin/activate
export OPENAI_API_KEY=sk-...   # optional
uvicorn src.backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs: http://localhost:8000/docs

---

## `tests/test_main.py`

Use `fastapi.testclient.TestClient` for all tests.

### Shared fixture — `SAMPLE_EXTRACTED`

```python
SAMPLE_EXTRACTED = {
    "extracted_id": "test-001",
    "ocr_confidence": 0.95,
    "bill_number": {"value": "B-2026-0001", "confidence": 0.99},
    "account_number": {"value": "123456789", "normalized": "123456789", "confidence": 0.98},
    "customer_name": {"value": "John Doe", "normalized": "john doe", "confidence": 0.95},
    "customer_address": ["1 Main St Athens"],
    "bill_date": {"value": "2026-01-15", "confidence": 0.98},
    "service_period": {"start": "2026-01-01", "end": "2026-01-31", "confidence": 0.97},
    "total_due": {"value": 152.34, "currency": "EUR", "confidence": 0.97},
    "line_items": [],
    "meter_ids": ["MTR-987"],
    "tariff_code": "T01",
    "match_hints": {"account_hash": "123456789", "name_norm": "john doe", "meter_list": ["MTR-987"]},
}
```

### Tests to write

| Test | Endpoint | Assertion |
|---|---|---|
| `test_health` | `GET /health` | `status == "ok"` |
| `test_upload_returns_extracted` | `POST /upload` | response has `extracted_id` and `agent` |
| `test_match_exact` | `POST /match` | `match_type == "exact"`, `matched_customer_id == "cust-42"` |
| `test_match_none` | `POST /match` | `match_type == "none"` for unknown account |
| `test_explain_returns_answer` | `POST /explain` | response has `answer`, `confidence_label`, `retrieved_passages` |

Run with: `python -m pytest src/backend/tests -v`

---

## Validation checklist

- [ ] CORS allows `http://localhost:3000`
- [ ] `.env` loaded at startup
- [ ] All 5 endpoints implemented
- [ ] `POST /upload` saves image + extracted JSON to disk
- [ ] `POST /pipeline` works even when image file is missing (uses stored extracted JSON)
- [ ] All 5 tests pass

---

## Next step → `ui/README.md`

