# src/api — FastAPI Bridge Server

Exposes the DEH billing pipeline as HTTP endpoints consumed by the Next.js UI.

## Run

```bash
# from the project root (c:\Users\alexa\Hackathon)
uvicorn src.api.main:app --reload --port 8000
```

Requires the project root to be the working directory so that `src.*` imports resolve correctly.

## Structure

```
src/api/
├── main.py            ← FastAPI app, CORS middleware, router registration
└── routers/
    ├── __init__.py
    ├── upload.py      ← POST /upload  (active)
    ├── match.py       ← POST /match   (not yet wired)
    └── explain.py     ← POST /explain (not yet wired)
```

To add a new endpoint: create `routers/<name>.py` with an `APIRouter`, then add one line to `main.py`:
```python
from src.api.routers import <name>
app.include_router(<name>.router)
```

## Endpoints

### `POST /upload`
Accepts a DEH electricity bill as one or two images.

| Field | Type | Description |
|---|---|---|
| `file_front` | `File` | Front page of the bill (required) |
| `file_back` | `File` | Back page of the bill (optional) |

**Flow:** saves to temp → Azure Document Intelligence OCR → `parse_front()` + `parse_back()` → merged JSON → deletes temp files.

**Returns:** flat JSON dict with all extracted bill fields (e.g. `vendor_name`, `invoice_total_eur`, `meter_readings`, …).

**Logs emitted:**
```
📥 Front: <filename>
📥 Back:  <filename>
🔍 OCR front page...
✅ Front — N lines
📤 Returning N fields
🗑️  Temp files cleaned up
```

### `GET /`
Health check — returns `{"status": "ok"}`.

## Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `AZURE_DOC_KEY` | `upload.py` (via `extractData.py`) | Azure Document Intelligence API key |

Set these in `.env` at the project root (loaded automatically via `python-dotenv`).

## CORS

Currently allows `http://localhost:3000` (Next.js dev server). Update `allow_origins` in `main.py` for production.
