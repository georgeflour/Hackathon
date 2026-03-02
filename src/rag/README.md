# Step 5 — RAG Module

Location: `src/rag/`

This module has two responsibilities:
1. **`prompt_package.py`** — assemble all context (bill, match, passages, instructions) into a single structured JSON object that gets handed to the LLM.
2. **`llm_runner.py`** — call the LLM with that package and return a structured answer.

---

## Files to create

| File | Purpose |
|---|---|
| `src/rag/__init__.py` | empty |
| `src/rag/prompt_package.py` | builds the RAG prompt package dict |
| `src/rag/llm_runner.py` | calls OpenAI GPT-4o or returns a stub answer |
| `src/rag/tests/__init__.py` | empty |
| `src/rag/tests/test_rag.py` | unit tests |

---

## `prompt_package.py`

### System instructions constant

Define a `SYSTEM_INSTRUCTIONS` string at module level. It must say:
- You are a helpful energy billing assistant.
- Answer ONLY using the facts in the `retrieved_passages` below.
- For every numeric or factual claim include an inline citation: `(Source: {doc_id}, page {page})`.
- If you cannot find support in the passages, say: `"I don't have enough information in the retrieved documents to answer this."`
- Never speculate. Never hallucinate.

### Public function

```python
def build_prompt_package(
    user_question: str,
    extracted_bill: dict,
    match_result: dict,
    retrieved_passages: list[dict],
) -> dict:
    ...
```

### Output shape

```python
{
  "package_id": str,                  # "pkg-{uuid4}"
  "created_at": str,                  # ISO 8601 UTC (timezone-aware)
  "system_instructions": str,
  "user_question": str,
  "extracted_bill_summary": {
      "bill_number": str | None,
      "account_number": str,
      "service_period": {"start": str, "end": str},
      "total_due": dict,
      "line_items": list,
      "meter_ids": list,
  },
  "matched_customer": dict,           # the full match_result dict
  "retrieval_queries": [              # for audit/explainability
      {"type": "metadata", "query_text": str},
      {"type": "semantic",  "query_text": str},
  ],
  "retrieved_passages": list[dict],
  "citation_policy": {
      "format": "(Source: {doc_id}, page {page})",
      "max_citations": 5,
      "require_citation_for_numeric_claims": True,
  },
  "hallucination_policy": {
      "disallow_external_facts": True,
      "unsupported_claim_action": "add_caveat",
  },
  "generation_parameters": {
      "temperature": 0.0,
      "max_tokens": 1024,
  },
}
```

### Build the `retrieval_queries` field automatically

```python
retrieval_queries = [
    {
        "type": "metadata",
        "query_text": f"customer_id={match_result.get('matched_customer_id')} account={acct} period={start} to {end}"
    },
    {
        "type": "semantic",
        "query_text": f"{user_question} account {acct} billing period {start} {end}"
    },
]
```

---

## `llm_runner.py`

### Data type

```python
@dataclass
class LlmAnswer:
    answer_text: str
    citations: list[dict]            # [{"doc_id": str, "page": int}]
    confidence_label: str            # "High" | "Medium" | "Low"
    confidence_score: float          # 0.0 – 1.0
    unsupported_claims: list[str]    # populated by ReplyAgent verifier
```

### Confidence calibration helper

```python
def _confidence_from_passages(passages: list[dict]) -> tuple[float, str]:
    if not passages:
        return 0.4, "Low"
    avg = sum(p.get("final_score", 0.7) for p in passages) / len(passages)
    label = "High" if avg >= 0.85 else ("Medium" if avg >= 0.65 else "Low")
    return round(avg, 3), label
```

### Stub mode (no API key)

When `OPENAI_API_KEY` is not set, return a templated answer that includes:
- The billing period, total due, and a note that this is stub mode.
- Up to 3 citations from the passages list.
- Confidence computed from passage scores.

This lets the full pipeline run and be tested without an API key.

### Real OpenAI call

When `OPENAI_API_KEY` is set:
1. Build a plain-text prompt from `_build_prompt(package)`.
2. The prompt must include: system instructions, bill summary, all retrieved passages (numbered), and the user question.
3. Call `client.chat.completions.create(model=..., temperature=0, max_tokens=1024)`.
4. Return the answer text. Citations parsing from inline text is a stretch goal.

### `_build_prompt(package)` structure

```
{system_instructions}

--- BILL SUMMARY ---
Bill number : {bill_number}
Account     : {account_number}
Period      : {start} → {end}
Total due   : {value} {currency}
Line items  : {line_items}

--- RETRIEVED PASSAGES ---
[1] doc_id={doc_id} page={page}
{text_snippet}

[2] ...

--- CUSTOMER QUESTION ---
{user_question}

Answer (with inline citations):
```

---

## `tests/test_rag.py`

### Tests to write

| Test | Assertion |
|---|---|
| `test_build_prompt_package_shape` | result has all required top-level keys |
| `test_package_id_is_unique` | two calls return different `package_id` |
| `test_system_instructions_present` | `"ONLY"` appears in system instructions (grounding policy) |
| `test_llm_runner_stub_returns_answer` | `run_llm(package)` returns `LlmAnswer` with non-empty `answer_text` |
| `test_confidence_low_with_no_passages` | `_confidence_from_passages([])` returns `(0.4, "Low")` |
| `test_confidence_high_with_good_scores` | passages with score 0.95 → label `"High"` |

---

## Validation checklist

- [ ] `SYSTEM_INSTRUCTIONS` explicitly forbids speculation and requires citations
- [ ] `build_prompt_package` returns all keys in the output shape
- [ ] `package_id` is always unique (uuid-based)
- [ ] `created_at` is timezone-aware ISO string (no `utcnow()`)
- [ ] `run_llm` works without `OPENAI_API_KEY` (stub mode)
- [ ] `run_llm` uses `temperature=0` for deterministic output
- [ ] All 6 tests pass

---

## Next step → `src/agents/README.md`

