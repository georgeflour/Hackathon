"""
extractor/ocr.py
----------------
Thin Tesseract OCR wrapper.

Returns OcrResult(raw_text, confidence).

To switch to a cloud provider (Google Vision, AWS Textract, Azure Form Recognizer)
replace the body of `run_ocr` with your API call and return the same OcrResult type.

Install requirements:
    pip install pytesseract Pillow
    brew install tesseract          # macOS
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OcrResult:
    raw_text: str
    confidence: float  # 0.0 – 1.0


def run_ocr(image_path: str | Path) -> OcrResult:
    """
    Extract raw text from a bill image using Tesseract.

    Parameters
    ----------
    image_path : path to a PNG / JPG bill image

    Returns
    -------
    OcrResult with raw_text and an averaged per-word confidence score.

    Raises
    ------
    ImportError  if pytesseract or Pillow are not installed.
    FileNotFoundError  if the image path does not exist.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "pytesseract and Pillow are required for local OCR.\n"
            "Install with: pip install pytesseract Pillow\n"
            "Also install the Tesseract binary: brew install tesseract"
        ) from exc

    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = Image.open(image_path)

    # Full text extraction
    raw_text: str = pytesseract.image_to_string(img)

    # Per-word confidence scores
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    confs = [int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0]
    confidence = round(sum(confs) / len(confs) / 100, 3) if confs else 0.5

    return OcrResult(raw_text=raw_text, confidence=confidence)

