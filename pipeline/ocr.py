"""Tesseract OCR fallback — text extraction, bounding boxes, and VLM merge."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PIL import Image

if TYPE_CHECKING:
    from models.schemas import InvoiceData

# ── Tesseract setup ───────────────────────────────────────────────────────────

def _find_tesseract() -> Optional[str]:
    """Return the explicit path to the tesseract binary, or None if not found."""
    for candidate in (
        "/opt/homebrew/bin/tesseract",   # Apple Silicon Mac (Homebrew)
        "/usr/local/bin/tesseract",       # Intel Mac (Homebrew)
        "/usr/bin/tesseract",             # Linux / Colab
        "/opt/local/bin/tesseract",       # MacPorts
    ):
        if Path(candidate).exists():
            return candidate
    return shutil.which("tesseract")     # fallback: check PATH


try:
    import pytesseract
    from pytesseract import Output as _Output

    _tess_path = _find_tesseract()
    if _tess_path:
        pytesseract.pytesseract.tesseract_cmd = _tess_path

    # Verify it actually runs
    pytesseract.get_tesseract_version()
    _TESSERACT_AVAILABLE = True

except Exception:
    _TESSERACT_AVAILABLE = False


# ── Core OCR ──────────────────────────────────────────────────────────────────

def ocr_extract_text(image: Image.Image) -> str:
    """Return raw OCR text, or empty string if Tesseract is unavailable."""
    if not _TESSERACT_AVAILABLE:
        return ""
    try:
        return pytesseract.image_to_string(image, config="--psm 6")
    except Exception:
        return ""


def ocr_extract_with_boxes(image: Image.Image) -> dict:
    """Return word-level bounding box data dict."""
    if not _TESSERACT_AVAILABLE:
        return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}
    try:
        return pytesseract.image_to_data(image, output_type=_Output.DICT, config="--psm 6")
    except Exception:
        return {"text": [], "conf": [], "left": [], "top": [], "width": [], "height": []}


def crop_region(image: Image.Image, keyword: str, padding: int = 20) -> Image.Image:
    """Crop image around first bbox containing keyword; fall back to full image."""
    data = ocr_extract_with_boxes(image)
    for i, word in enumerate(data.get("text", [])):
        if keyword.lower() in str(word).lower() and int(data["conf"][i]) > 0:
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            box = (
                max(0, x - padding), max(0, y - padding),
                min(image.width, x + w + padding), min(image.height, y + h + padding),
            )
            return image.crop(box)
    return image


# ── OCR ↔ VLM merge ───────────────────────────────────────────────────────────

def merge_ocr_with_extraction(ocr_text: str, extracted: "InvoiceData") -> "InvoiceData":
    """Fill None fields in extracted data using OCR text regex patterns."""
    data = extracted.model_copy(deep=True)

    if data.invoice_date is None:
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", ocr_text)
        if m:
            data.invoice_date = m.group(1)
        else:
            m = re.search(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b", ocr_text)
            if m:
                data.invoice_date = f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    if data.invoice_number is None:
        m = re.search(
            r"(?:invoice\s*(?:#|no\.?|number)?|inv\.?)[:\s#]*([A-Z0-9\-]{4,20})",
            ocr_text, re.IGNORECASE,
        )
        if m:
            data.invoice_number = m.group(1).strip()

    if data.vendor_name is None:
        lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]
        if lines:
            data.vendor_name = lines[0][:80]

    if data.total_amount is None:
        m = re.search(
            r"(?:total|amount\s*due|balance\s*due)[^\d]*(\d[\d,]*\.?\d{0,2})",
            ocr_text, re.IGNORECASE,
        )
        if m:
            try:
                data.total_amount = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    if data.tax_amount is None:
        m = re.search(
            r"(?:tax|vat|gst)[^\d]*(\d[\d,]*\.?\d{0,2})",
            ocr_text, re.IGNORECASE,
        )
        if m:
            try:
                data.tax_amount = float(m.group(1).replace(",", ""))
            except ValueError:
                pass

    if data.subtotal is None and data.total_amount and data.tax_amount:
        data.subtotal = round(data.total_amount - data.tax_amount, 2)

    return data
