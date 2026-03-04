"""
src/api/routers/upload.py — POST /upload
Accepts file_front (required) and file_back (optional).
Runs parse_front on the first file and parse_back on the second.
Returns merged JSON.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi import Form

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.backend.extractData import get_ocr_lines, parse_front, parse_back

logger = logging.getLogger("upload")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")

router = APIRouter(tags=["upload"])


async def _save_temp(file: UploadFile) -> str:
    suffix = Path(file.filename or "bill").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        return tmp.name


@router.post("/upload")
async def upload_bill(
    file_front: UploadFile = File(...),
    file_back: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    """
    Receive 1 or 2 bill images:
      file_front — front page  → parse_front()
      file_back  — back page   → parse_back()  (optional)
    Returns merged extracted fields.
    """
    logger.info("📥 Front: %s", file_front.filename)
    if file_back and file_back.filename:
        logger.info("📥 Back:  %s", file_back.filename)

    tmp_front = tmp_back = None
    try:
        # ── front page ────────────────────────────────────────────────
        tmp_front = await _save_temp(file_front)
        logger.info("🔍 OCR front page...")
        front_lines = get_ocr_lines(tmp_front)
        logger.info("✅ Front — %d lines", len(front_lines))
        data: dict[str, Any] = parse_front(front_lines)
        data["source_file_front"] = file_front.filename

        # ── back page (optional) ──────────────────────────────────────
        if file_back and file_back.filename:
            tmp_back = await _save_temp(file_back)
            logger.info("🔍 OCR back page...")
            back_lines = get_ocr_lines(tmp_back)
            logger.info("✅ Back  — %d lines", len(back_lines))
            back_data = parse_back(back_lines)
            back_data.pop("source_file_front", None)
            back_data["source_file_back"] = file_back.filename
            # front fields take priority on collision
            data = {**back_data, **data}

        logger.info("📤 Returning %d fields", len(data))
        return data

    except Exception as exc:
        logger.error("❌ %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        for p in (tmp_front, tmp_back):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass
        logger.info("🗑️  Temp files cleaned up")
