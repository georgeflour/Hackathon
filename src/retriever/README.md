# Step 4 — Retriever Module

Location: `src/retriever/`

This module retrieves relevant passages from the knowledge corpus in `data/knowledge/`. The ReplyAgent calls it with multiple queries and deduplicates results before passing them to the LLM.

---

## Files to create

| File | Purpose |
|---|---|
| `src/retriever/__init__.py` | empty |
| `src/retriever/retriever.py` | BM25 keyword retriever |
| `src/retriever/tests/__init__.py` | empty |
| `src/retriever/tests/test_retriever.py` | unit tests |

---

## `retriever.py`

### Public function

```python
def retrieve(
    query: str,
    customer_id: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    ...
```

### Output shape — one passage dict per result

```python
{
  "passage_id": str,        # "{doc_id}-p{page}"
  "doc_id":     str,
  "doc_title":  str,
  "page":       int,
  "text_snippet": str,      # first 400 characters of document text
  "source_uri": str,        # absolute path to the .json file
  "final_score": float,     # 0.0 – 1.0
}
```

### Implementation

**Loading the corpus**

```python
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge"

def _load_corpus() -> list[dict]:
    docs = []
    for f in KNOWLEDGE_DIR.glob("*.json"):
        try:
            docs.append(json.loads(f.read_text()))
        except Exception:
            pass
    return docs
```

**BM25-style scoring**

```python
def _bm25_score(query_tokens: list[str], doc_text: str) -> float:
    text_lower = doc_text.lower()
    hits = sum(1 for t in query_tokens if t in text_lower)
    return hits / max(len(query_tokens), 1)
```

**`retrieve` function logic**

1. Call `_load_corpus()`.
2. Tokenize query: `tokens = re.findall(r"\w+", query.lower())`.
3. Score every doc with `_bm25_score(tokens, doc["text"])`.
4. Filter docs where `final_score > 0`, sort descending, take top `top_k`.
5. Return list of passage dicts (reshape to output shape above).
6. If corpus is empty → return `[]`.

### Stretch upgrade path (do not implement now, note for later)

To upgrade to vector search:
- Replace `_bm25_score` with cosine similarity using `sentence-transformers`.
- Use FAISS index stored at `data/knowledge/index.faiss`.
- Keep the same public `retrieve` interface — nothing else changes.

---

## `tests/test_retriever.py`

### Setup

Create a `tmp_knowledge` fixture that writes two minimal JSON docs to a temp dir and monkeypatches `KNOWLEDGE_DIR`.

### Tests to write

| Test | Assertion |
|---|---|
| `test_retrieve_returns_list` | result is a list |
| `test_retrieve_relevant_doc` | query `"regulated charges"` returns doc with `doc_id == "faq-002"` |
| `test_retrieve_top_k_respected` | `len(retrieve(query, top_k=2)) <= 2` |
| `test_retrieve_empty_corpus` | returns `[]` when no docs exist |
| `test_passage_shape` | every result has `passage_id`, `doc_id`, `text_snippet`, `final_score` |

Run with: `python -m pytest src/retriever/tests -v`

---

## Validation checklist

- [ ] `retrieve` loads all `*.json` files from `data/knowledge/` automatically
- [ ] Returns empty list gracefully when folder is empty or missing
- [ ] Each result has all required passage fields
- [ ] `final_score` is between 0 and 1
- [ ] All 5 tests pass

---

## Next step → `src/rag/README.md`

