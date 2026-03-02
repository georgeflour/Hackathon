# Step 6 — Agents Module

Location: `src/agents/`

This is the core of the project. The three agents wrap the lower-level modules and expose a clean, testable interface. The orchestrator chains them into the full pipeline.

---

## Files to create

| File | Purpose |
|---|---|
| `src/agents/__init__.py` | empty |
| `src/agents/vision_agent.py` | Agent 1 — extraction |
| `src/agents/matcher_agent.py` | Agent 2 — DWH matching + enrichment |
| `src/agents/reply_agent.py` | Agent 3 — retrieval + RAG + verifier |
| `src/agents/orchestrator.py` | chains all three agents |
| `src/agents/tests/__init__.py` | empty |
| `src/agents/tests/test_agents.py` | end-to-end agent tests |

---

## Agent 1 — `vision_agent.py`

### Responsibility
Convert a bill image path → `VisionResult`.

### Data type

```python
@dataclass
class VisionResult:
    extracted: dict          # full ExtractedBill JSON
    ocr_confidence: float
    extraction_method: str   # "llm_vision" | "rule_based"
    agent_name: str = "VisionAgent"
```

### Logic

```
if OPENAI_API_KEY is set:
    call GPT-4o with image as base64 + VISION_SYSTEM_PROMPT
    parse JSON response → normalise to ExtractedBill shape
    return VisionResult(extraction_method="llm_vision")
else:
    try run_ocr(image_path)     # from src/extractor/ocr.py
    call extract_fields(ocr.raw_text, ocr.confidence)   # from src/extractor/parser.py
    return VisionResult(extraction_method="rule_based")
```

### GPT-4o vision system prompt

Define `VISION_SYSTEM_PROMPT` as a constant. It must instruct GPT-4o to return **only valid JSON** with these fields:

```json
{
  "bill_number": "string|null",
  "account_number": "string|null",
  "customer_name": "string|null",
  "customer_address": ["string"],
  "bill_date": "YYYY-MM-DD|null",
  "service_period_start": "YYYY-MM-DD|null",
  "service_period_end": "YYYY-MM-DD|null",
  "total_due_value": "number|null",
  "total_due_currency": "string|null",
  "meter_ids": ["string"],
  "tariff_code": "string|null",
  "line_items": [{"description": "str", "quantity_kwh": "num|null", "unit_price": "num|null", "amount": "num|null"}]
}
```

### `_normalise_llm_output(raw, ocr_confidence)` helper

Map GPT-4o field names → the internal `ExtractedBill` schema (same shape as `schemas/extracted_bill_example.json`). This function must:
- Generate a new `extracted_id` (uuid4).
- Set `extraction_timestamp` to `datetime.now(timezone.utc).isoformat()`.
- Wrap each field in `{"value": ..., "confidence": 0.97 if not None else 0.0}`.

---

## Agent 2 — `matcher_agent.py`

### Responsibility
Receive the `ExtractedBill` dict → run `match_customer` → enrich with full DWH context → return `MatcherResult`.

### Data type

```python
@dataclass
class MatcherResult:
    match_type: str                    # "exact"|"fuzzy_high"|"fuzzy_ambiguous"|"none"
    matched_customer_id: str | None
    score: float
    candidates: list[dict]
    clarifying_question: str | None
    customer_context: dict             # row from Customer_Context.csv
    billing_history: list[dict]        # rows from Billing_Header.csv for this customer
    agent_name: str = "MatcherAgent"
```

### Logic

```python
def run_matcher_agent(extracted: dict) -> MatcherResult:
    match = match_customer(extracted)          # from src/matcher/match_service.py
    if match.matched_customer_id:
        customer_context = load Customer_Context row for that customer_id
        billing_history  = load all Billing_Header rows for that customer_id
    return MatcherResult(...)
```

### DWH enrichment helpers

```python
def _get_customer_context(customer_id: str) -> dict:
    df = pd.read_csv(CUSTOMER_CSV, dtype=str)
    row = df[df["customer_id"] == customer_id]
    return row.iloc[0].to_dict() if not row.empty else {}

def _get_billing_history(customer_id: str) -> list[dict]:
    df = pd.read_csv(HEADER_CSV, dtype=str)
    return df[df["customer_id"] == customer_id].to_dict(orient="records")
```

---

## Agent 3 — `reply_agent.py`

### Responsibility
Build multi-query retrieval → assemble prompt package → call LLM → verify claims → return `ReplyResult`.

### Data type

```python
@dataclass
class ReplyResult:
    answer_text: str
    citations: list[dict]
    confidence_label: str
    confidence_score: float
    unsupported_claims: list[str]
    prompt_package_id: str
    retrieved_passages: list[dict]
    agent_name: str = "ReplyAgent"
```

### Multi-query strategy

Build **3 queries** from the extracted bill + match context:
- **Q1** (semantic) — user question + account + period + total
- **Q2** (tariff/charges focused) — `"tariff {tariff_code} energy charge regulated charges kWh increase"`
- **Q3** (policy focused) — `"billing policy regulated charges dispute explanation VAT network charge"`

Call `retrieve(query, customer_id, top_k=3)` for each query.
Deduplicate by `passage_id`, sort by `final_score` descending, keep top 6.

### Prompt enrichment

Before calling `build_prompt_package`, merge customer context and billing history into the extracted dict:
```python
enriched = {
    **extracted,
    "customer_context": matcher_result["customer_context"],
    "billing_history":  matcher_result["billing_history"],
}
```

### Post-generation claim verifier

After the LLM returns `answer_text`:
1. Split into sentences.
2. For each sentence containing a digit (these are factual/numeric claims):
   - Extract all numbers from the sentence.
   - Check if any number appears in the concatenated passage texts.
   - If none match → add sentence to `unsupported_claims`.
3. If `unsupported_claims` is non-empty → append a caveat to `answer_text`:
   ```
   ⚠️ Note: the following claims could not be verified against retrieved documents:
   - {claim 1}
   - {claim 2}
   ```

---

## `orchestrator.py`

### Public function

```python
def run_pipeline(
    image_path: str | Path,
    question: str,
    extra_passages: list[dict] | None = None,
) -> dict:
    vision  = run_vision_agent(image_path)
    matcher = run_matcher_agent(vision.extracted)
    reply   = run_reply_agent(
        question=question,
        vision_result=vision.extracted,
        matcher_result=asdict(matcher),
        extra_passages=extra_passages,
    )
    return {
        "answer":            reply.answer_text,
        "citations":         reply.citations,
        "confidence_label":  reply.confidence_label,
        "confidence_score":  reply.confidence_score,
        "unsupported_claims": reply.unsupported_claims,
        "prompt_package_id": reply.prompt_package_id,
        "agent1_vision":  {"extracted": vision.extracted, "ocr_confidence": vision.ocr_confidence, "extraction_method": vision.extraction_method},
        "agent2_matcher": asdict(matcher),
        "agent3_reply":   {"retrieved_passages": reply.retrieved_passages},
    }
```

---

## `tests/test_agents.py`

### Shared fixture — `SAMPLE_EXTRACTED`

Use the dict from `schemas/extracted_bill_example.json` as your test fixture (account `123456789`, meter `MTR-987`, customer `cust-42`).

### Tests to write

| Test | Agent | Assertion |
|---|---|---|
| `test_vision_agent_rule_based` | Agent 1 | creates a `.txt` bill file, calls `run_vision_agent`, checks `account_number.normalized == "123456789"` |
| `test_matcher_agent_exact_match` | Agent 2 | `match_type == "exact"`, `matched_customer_id == "cust-42"` |
| `test_matcher_enriches_context` | Agent 2 | `customer_context["customer_name"] == "John Doe"` |
| `test_matcher_enriches_history` | Agent 2 | `len(billing_history) >= 1` |
| `test_matcher_no_match` | Agent 2 | `match_type == "none"` for unknown account |
| `test_reply_returns_answer` | Agent 3 | `answer_text` is non-empty string |
| `test_reply_has_passages` | Agent 3 | `len(retrieved_passages) > 0` |
| `test_orchestrator_end_to_end` | All | `"answer"` and `"agent2_matcher"` keys exist, `match_type == "exact"` |

Run with: `python -m pytest src/agents/tests -v`

---

## Validation checklist

- [ ] `VisionResult`, `MatcherResult`, `ReplyResult` dataclasses defined with `agent_name` field
- [ ] VisionAgent uses LLM when key available, rule-based otherwise
- [ ] MatcherAgent returns `customer_id` (e.g. `cust-42`), not account number
- [ ] ReplyAgent runs 3 queries, deduplicates, keeps top 6
- [ ] Claim verifier appends caveat when numeric claims are unverified
- [ ] Orchestrator returns per-agent outputs in result dict
- [ ] All 8 tests pass

---

## Next step → `src/backend/README.md`

