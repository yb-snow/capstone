"""Auto-Correction Agent — re-queries the VLM with a focused crop on failed fields."""

from __future__ import annotations

import json
import re
from typing import Optional

from PIL import Image

from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    MAX_CORRECTION_ATTEMPTS, VLM_BACKEND,
)
from models.schemas import ExtractionResult, FieldValidation, ValidationResult, ValidationStatus
from pipeline.ocr import crop_region
from utils.image_processing import image_to_base64

_CORRECTION_PROMPT = """A field in this document failed validation.

Field: {field}
Current extracted value: {current_value}
Validation error: {error_message}

Look carefully at the image crop and re-extract ONLY the "{field}" field.
Return ONLY this JSON object, nothing else:
{{"field": "{field}", "value": <corrected value or null>}}

Rules:
- Amounts = plain numbers (no currency symbols)
- Dates = YYYY-MM-DD
- Return ONLY the JSON, no explanation."""

_FIELD_KEYWORDS = {
    "total_amount":  "total",
    "subtotal":      "subtotal",
    "tax_amount":    "tax",
    "invoice_date":  "date",
    "due_date":      "due",
    "invoice_number":"invoice",
    "vendor_name":   "vendor",
    "iban":          "iban",
}


def run(
    image: Image.Image,
    extraction: ExtractionResult,
    validation: ValidationResult,
) -> ExtractionResult:
    updated = extraction.extracted_data.model_copy(deep=True)

    for field in validation.failed_fields:
        fv      = next((v for v in validation.field_validations if v.field == field), None)
        current = str(getattr(updated, field, ""))
        error   = fv.message if fv else ""

        corrected = _attempt_correction(image, field, current, error)
        if corrected is not None:
            try:
                setattr(updated, field, corrected)
            except Exception:
                pass

    return ExtractionResult(
        raw_ocr_text=extraction.raw_ocr_text,
        extracted_data=updated,
        confidence=extraction.confidence,
        vlm_response=extraction.vlm_response,
    )


def _attempt_correction(image: Image.Image, field: str, current: str, error: str) -> Optional[str]:
    keyword = _FIELD_KEYWORDS.get(field, field.replace("_", " "))
    crop    = crop_region(image, keyword) or image
    prompt  = _CORRECTION_PROMPT.format(
        field=field, current_value=current, error_message=error
    )

    if VLM_BACKEND == "gemini":
        return _correct_with_gemini(crop, prompt)
    elif VLM_BACKEND == "claude":
        return _correct_with_claude(crop, prompt)
    return None


# ── Gemini (free, recommended) ────────────────────────────────────────────────

def _correct_with_gemini(crop: Image.Image, prompt: str) -> Optional[str]:
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    response = model.generate_content(
        [crop, prompt],
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=256,
            temperature=0.1,
        ),
    )
    return _parse_correction(response.text)


# ── Claude (optional, paid) ───────────────────────────────────────────────────

def _correct_with_claude(crop: Image.Image, prompt: str) -> Optional[str]:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64    = image_to_base64(crop, fmt="PNG")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return _parse_correction(message.content[0].text)


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse_correction(text: str) -> Optional[str]:
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{[\s\S]*?\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group()).get("value")
    except Exception:
        return None
