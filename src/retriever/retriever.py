"""
retriever/retriever.py
----------------------
Knowledge-corpus retriever with two backends:

  VECTOR (default)
    sentence-transformers all-MiniLM-L6-v2  +  FAISS flat index
    Index is built on first call and cached in data/knowledge/index.faiss
    + data/knowledge/index_meta.json (doc metadata).
    Subsequent calls load the cached index (fast start-up).

  BM25 fallback
    Pure-Python keyword overlap — used when sentence-transformers /
    faiss-cpu are not installed, or when forced via RETRIEVER_BACKEND=bm25.

Public interface (identical for both backends)
----------------------------------------------
    from src.retriever.retriever import retrieve

    passages = retrieve(
        query="Why is my bill higher?",
        customer_id="cust-42",   # optional, reserved for future DWH-linked docs
        top_k=5,
    )

Each passage dict:
    {
      "passage_id":   str,          # "{doc_id}-p{page}"
      "doc_id":       str,
      "doc_title":    str,
      "page":         int,
      "text_snippet": str,          # first 400 chars of document text
      "source_uri":   str,          # absolute path to .json file
      "final_score":  float,        # 0.0 – 1.0
    }
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ─── paths ────────────────────────────────────────────────────────────────────
_KNOWLEDGE_DIR  = Path(__file__).parent.parent.parent / "data" / "knowledge"
_INDEX_PATH     = _KNOWLEDGE_DIR / "index.faiss"
_META_PATH      = _KNOWLEDGE_DIR / "index_meta.json"
_MODEL_NAME     = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
_BACKEND        = os.getenv("RETRIEVER_BACKEND", "vector").lower()   # "vector" | "bm25"

# Module-level singletons (lazy-loaded)
_index   = None   # faiss.IndexFlatIP
_meta    : list[dict[str, Any]] = []
_model   = None   # SentenceTransformer


# ─── corpus loader ────────────────────────────────────────────────────────────

def _load_corpus() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    if not _KNOWLEDGE_DIR.exists():
        return docs
    for f in sorted(_KNOWLEDGE_DIR.glob("*.json")):
        try:
            docs.append(json.loads(f.read_text()))
        except Exception:
            logger.warning("Could not parse knowledge file: %s", f)
    return docs


# ─── BM25 fallback ────────────────────────────────────────────────────────────

def _bm25_score(query_tokens: list[str], doc_text: str) -> float:
    text_lower = doc_text.lower()
    hits = sum(1 for t in query_tokens if t in text_lower)
    return hits / max(len(query_tokens), 1)


def _bm25_retrieve(query: str, top_k: int) -> list[dict[str, Any]]:
    corpus = _load_corpus()
    if not corpus:
        return []
    tokens = re.findall(r"\w+", query.lower())
    scored = [
        {**doc, "final_score": round(_bm25_score(tokens, doc.get("text", "")), 3)}
        for doc in corpus
    ]
    scored.sort(key=lambda d: d["final_score"], reverse=True)
    return [d for d in scored if d["final_score"] > 0][:top_k]


# ─── vector backend ───────────────────────────────────────────────────────────

def _build_index(corpus: list[dict[str, Any]]) -> None:
    """Encode corpus and save FAISS index + metadata to disk."""
    global _index, _meta, _model
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    logger.info("Building FAISS index for %d documents…", len(corpus))
    _model = SentenceTransformer(_MODEL_NAME)
    texts   = [doc.get("text", "") for doc in corpus]
    embeds  = _model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    embeds  = np.array(embeds, dtype="float32")

    dim    = embeds.shape[1]
    index  = faiss.IndexFlatIP(dim)   # inner-product on L2-normalised vectors = cosine
    index.add(embeds)

    faiss.write_index(index, str(_INDEX_PATH))

    _meta = [
        {
            "doc_id":    doc.get("doc_id", f"doc-{i}"),
            "doc_title": doc.get("title", ""),
            "page":      doc.get("page", 1),
            "text":      doc.get("text", ""),
            "source_uri": str(_KNOWLEDGE_DIR / f"{doc.get('doc_id', f'doc-{i}')}.json"),
        }
        for i, doc in enumerate(corpus)
    ]
    _META_PATH.write_text(json.dumps(_meta, ensure_ascii=False, indent=2))
    _index = index
    logger.info("FAISS index built and saved.")


def _load_index() -> bool:
    """Load a previously built index from disk. Returns True on success."""
    global _index, _meta, _model
    if not _INDEX_PATH.exists() or not _META_PATH.exists():
        return False
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        _index = faiss.read_index(str(_INDEX_PATH))
        _meta  = json.loads(_META_PATH.read_text())
        _model = SentenceTransformer(_MODEL_NAME)
        return True
    except Exception as exc:
        logger.warning("Could not load FAISS index: %s", exc)
        return False


def _ensure_index() -> bool:
    """Ensure the FAISS index is ready. Returns True if vector search is available."""
    global _index
    if _index is not None:
        return True
    # Try loading from disk first (fast)
    if _load_index():
        return True
    # Build from scratch
    corpus = _load_corpus()
    if not corpus:
        return False
    try:
        _build_index(corpus)
        return True
    except Exception as exc:
        logger.warning("FAISS index build failed (%s) — falling back to BM25.", exc)
        return False


def _vector_retrieve(query: str, top_k: int) -> list[dict[str, Any]]:
    import numpy as np

    if not _ensure_index():
        return _bm25_retrieve(query, top_k)

    q_embed = _model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    q_embed = np.array(q_embed, dtype="float32")

    k       = min(top_k, len(_meta))
    scores, indices = _index.search(q_embed, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        m = _meta[idx]
        results.append({**m, "final_score": round(float(score), 4)})
    return results


# ─── public interface ─────────────────────────────────────────────────────────

def retrieve(
    query: str,
    customer_id: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve top-k relevant passages from the knowledge corpus.

    Parameters
    ----------
    query       : free-text question / retrieval query
    customer_id : optional — reserved for future customer-scoped documents
    top_k       : maximum passages to return

    Returns
    -------
    List of passage dicts sorted by final_score descending.
    """
    use_vector = (_BACKEND == "vector")

    raw_results = _vector_retrieve(query, top_k) if use_vector else _bm25_retrieve(query, top_k)

    # Reshape to the standard passage format
    passages: list[dict[str, Any]] = []
    for r in raw_results:
        passages.append({
            "passage_id":   f"{r.get('doc_id', '?')}-p{r.get('page', 1)}",
            "doc_id":       r.get("doc_id", "unknown"),
            "doc_title":    r.get("doc_title") or r.get("title", ""),
            "page":         r.get("page", 1),
            "text_snippet": (r.get("text", ""))[:400],
            "source_uri":   r.get("source_uri", ""),
            "final_score":  r.get("final_score", 0.0),
        })

    return passages


def invalidate_index() -> None:
    """Delete the cached FAISS index so it is rebuilt on the next retrieve() call."""
    global _index, _meta, _model
    _index = _meta_data = _model = None
    for p in (_INDEX_PATH, _META_PATH):
        if p.exists():
            p.unlink()

