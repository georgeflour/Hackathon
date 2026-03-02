# Step 1 — RAG Knowledge Corpus

This folder contains the documents that the ReplyAgent retrieves to ground its answers.
Every file is a flat JSON with a fixed schema. The retriever loads all `*.json` files at query time — no restart needed after adding documents.

---

## Document schema

Each file must be valid JSON with these fields:

```json
{
  "doc_id":  "string — unique identifier, e.g. faq-001",
  "title":   "string — human-readable title shown as citation",
  "page":    1,
  "text":    "string — full document text used for retrieval and LLM context"
}
```

- `doc_id` must be unique across all files in this folder.
- `text` should be self-contained (the LLM sees only this field).
- Keep each document focused on one topic — this improves retrieval precision.

---

## Documents to create

Create one `.json` file per document below.

### faq-001.json — Why did my bill increase?

Cover: higher consumption, seasonal changes, new appliances, rate adjustments.

### faq-002.json — What are regulated charges?

Cover: network use-of-system (UoS) charges, renewable energy levy, capacity mechanism charge, PSO levy. State that these are set by the national regulator and are outside the supplier's control.

### faq-003.json — How is VAT calculated?

Cover: VAT rate (13%), what it applies to (energy + network charges), how it appears as a line item.

### faq-004.json — What is an estimated bill?

Cover: when a meter read is unavailable, how estimated bills are issued, how the difference is settled on the next actual-read bill.

### tariff-T01.json — Residential Tariff T01 (2026)

Cover: energy charge rate (e.g. 0.12 EUR/kWh up to 500 kWh, 0.15 above), standing charge, regulated network charge rate, VAT rate, effective date.

### tariff-T02.json — Business Tariff T02 (2026)

Cover: business energy rate, demand charges, network charges, VAT, effective date.

### policy-billing-001.json — Billing Dispute Procedure

Cover: how to raise a dispute (within 30 days), steps (contact customer service, provide account + bill number), investigation timeline (10 business days), credit adjustment process.

### policy-billing-002.json — Direct Debit & Payment Policy

Cover: payment methods, direct debit setup, late payment charges, payment plan options.

---

## Example file

```json
{
  "doc_id": "faq-001",
  "title": "Why did my electricity bill increase?",
  "page": 1,
  "text": "Your electricity bill may increase for several reasons: ..."
}
```

---

## Retrieval behaviour

The BM25 retriever in `src/retriever/retriever.py` scores each document by keyword overlap with the query. The ReplyAgent sends **3 queries** per request (semantic, tariff-focused, policy-focused) and deduplicates results, keeping the top 6 passages ranked by score.

Citations in the LLM answer use:
```
(Source: {doc_id}, page {page})
```

---

## Validation checklist

- [ ] All 8 documents created as `.json` files in this folder
- [ ] Each file has `doc_id`, `title`, `page`, `text` fields
- [ ] No duplicate `doc_id` values
- [ ] `text` is detailed enough (≥ 100 words) for the LLM to cite specific facts
- [ ] Tariff rates match what is used in `data/dwh/Billing_Lines.csv`

---

## Next step → `src/extractor/README.md`

