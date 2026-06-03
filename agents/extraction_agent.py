"""Extraction Agent — classifies document type AND extracts all fields in one VLM call."""

from __future__ import annotations

import json
import re
from typing import Tuple

from PIL import Image

import config
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, GEMINI_API_KEY, GEMINI_MODEL
from models.schemas import DocumentData, ExtractionResult

# One prompt does BOTH classification and full extraction — saves an API call
_PROMPT = """You are an expert document analyst. Examine this document image carefully.

Your task:
1. Identify the document type
2. Extract EVERY piece of information visible in the document — be exhaustive

Return ONLY valid JSON in this exact structure (no markdown fences, no explanation):
{{
  "doc_type": "<invoice|receipt|purchase_order|bank_statement|expense_report|quote|delivery_note|contract|form|other>",
  "doc_subtype": "<optional: e.g. tax_invoice, pro_forma, credit_note, utility_bill>",
  "confidence": <0.0 to 1.0>,
  "fields": {{
    // Include EVERY field you can read from the document
    // Use clear snake_case keys, e.g.:
    //   vendor_name, invoice_number, invoice_date, due_date,
    //   billing_address, shipping_address, phone, email,
    //   subtotal, tax_rate, tax_amount, discount, total_amount,
    //   currency, payment_terms, iban, account_number, bank_name,
    //   purchase_order_number, customer_name, customer_id, notes
    // Dates → YYYY-MM-DD format
    // Amounts → plain numbers without currency symbols
    // Use null only for fields clearly present but unreadable
    // Do NOT include fields that don't exist in this document
  }},
  "line_items": [
    // Every row from any table (products, services, transactions)
    // Include ALL columns that appear in the table
    // E.g.: {{"description": "...", "quantity": 1, "unit_price": 100.00, "total": 100.00}}
  ],
  "extraction_notes": "<one sentence: what type of document and key facts found>"
}}

OCR TEXT (use as reference if image is unclear):
{ocr_text}"""


def run(image: Image.Image, ocr_text: str) -> ExtractionResult:
    backend = config.VLM_BACKEND          # read at call-time so Settings changes take effect
    if backend == "gemini":
        return _extract_with_gemini(image, ocr_text)
    elif backend == "claude":
        return _extract_with_claude(image, ocr_text)
    elif backend == "mlx":
        return _extract_with_mlx(image, ocr_text)
    elif backend == "moondream":
        return _extract_with_moondream(image, ocr_text)
    elif backend in ("internvl", "llava"):
        return _extract_with_local_vlm(image, ocr_text)
    raise ValueError(f"Unknown VLM_BACKEND: '{backend}'. Valid: gemini, claude, mlx, moondream")


# ── Gemini ────────────────────────────────────────────────────────────────────

def _extract_with_gemini(image: Image.Image, ocr_text: str) -> ExtractionResult:
    from google import genai
    from google.genai import types

    client   = genai.Client(api_key=GEMINI_API_KEY)
    prompt   = _PROMPT.format(ocr_text=ocr_text[:4000])

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[image, prompt],
        config=types.GenerateContentConfig(max_output_tokens=4096, temperature=0.1),
    )
    return _build_result(ocr_text, response.text)


# ── Claude ────────────────────────────────────────────────────────────────────

def _extract_with_claude(image: Image.Image, ocr_text: str) -> ExtractionResult:
    import anthropic
    from utils.image_processing import image_to_base64

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64    = image_to_base64(image, fmt="PNG")
    prompt = _PROMPT.format(ocr_text=ocr_text[:4000])

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text",  "text": prompt},
        ]}],
    )
    return _build_result(ocr_text, msg.content[0].text)


# ── Apple MLX (M-chip, no API key) ───────────────────────────────────────────

def _extract_with_mlx(image: Image.Image, ocr_text: str) -> ExtractionResult:
    """Run a 4-bit quantised vision model via Apple MLX — fast on M1/M2/M3/M4."""
    try:
        import mlx_vlm
        from mlx_vlm import load, generate
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config as mlx_load_config
    except ImportError as e:
        raise ImportError("Install mlx-vlm: pip install mlx-vlm") from e

    model_path = config.LOCAL_VLM_MODEL   # e.g. "mlx-community/llava-1.5-7b-4bit"
    print(f"[MLX] Loading {model_path} (downloads on first use)…")

    model, processor = load(model_path)
    mlx_cfg          = mlx_load_config(model_path)
    prompt           = _PROMPT.format(ocr_text=ocr_text[:3000])
    chat_prompt      = apply_chat_template(processor, mlx_cfg, prompt, num_images=1)

    # Save image to temp file (mlx_vlm expects a path or URL)
    import tempfile, os
    from PIL import Image as PILImage
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw = generate(model, processor, tmp_path, chat_prompt,
                       verbose=False, max_tokens=2048)
    finally:
        os.unlink(tmp_path)

    return _build_result(ocr_text, raw)


# ── moondream2 (tiny, CPU/MPS, no API key) ────────────────────────────────────

def _extract_with_moondream(image: Image.Image, ocr_text: str) -> ExtractionResult:
    """Run moondream2 (~2 GB) locally — works on CPU or Apple MPS."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        raise ImportError("Install transformers: pip install transformers einops") from e

    import torch

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model_id = "vikhyatk/moondream2"
    print(f"[moondream2] Loading on {device.upper()} (downloads on first use ~2 GB)…")

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=True,
        torch_dtype=torch.float16 if device == "mps" else torch.float32,
    ).to(device).eval()

    prompt = _PROMPT.format(ocr_text=ocr_text[:3000])
    enc_image = model.encode_image(image)

    with torch.no_grad():
        raw = model.answer_question(enc_image, prompt, tokenizer)

    return _build_result(ocr_text, raw)


# ── Local VLM (HuggingFace InternVL2 / LLaVA) ────────────────────────────────

def _extract_with_local_vlm(image: Image.Image, ocr_text: str) -> ExtractionResult:
    from config import LOCAL_VLM_DEVICE, LOCAL_VLM_MODEL
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as e:
        raise ImportError("Install transformers and torch for local VLM support.") from e

    tokenizer = AutoTokenizer.from_pretrained(LOCAL_VLM_MODEL, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        LOCAL_VLM_MODEL, torch_dtype=torch.float16,
        device_map=LOCAL_VLM_DEVICE, trust_remote_code=True,
    ).eval()
    prompt = _PROMPT.format(ocr_text=ocr_text[:4000])
    inputs = tokenizer(prompt, return_tensors="pt").to(LOCAL_VLM_DEVICE)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=2048)
    return _build_result(ocr_text, tokenizer.decode(out[0], skip_special_tokens=True))


# ── Parse helpers ─────────────────────────────────────────────────────────────

def _build_result(ocr_text: str, raw: str) -> ExtractionResult:
    doc_data, confidence = _parse_response(raw)
    return ExtractionResult(
        raw_ocr_text=ocr_text,
        extracted_data=doc_data,
        confidence=confidence,
        vlm_response=raw,
    )


def _parse_response(text: str) -> Tuple[DocumentData, float]:
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return DocumentData(), 0.0
    try:
        obj = json.loads(match.group())

        doc_type  = str(obj.get("doc_type", "unknown")).lower().replace(" ", "_")
        subtype   = obj.get("doc_subtype")
        raw_conf  = float(obj.get("confidence", 0.5))
        fields    = obj.get("fields") or {}
        items     = obj.get("line_items") or []
        notes     = obj.get("extraction_notes", "")

        # Normalise field values — strip currency symbols from amounts
        clean_fields: dict = {}
        for k, v in fields.items():
            if isinstance(v, str):
                cleaned = v.strip()
                clean_fields[k] = cleaned if cleaned else None
            else:
                clean_fields[k] = v

        # Confidence = VLM confidence weighted by how many fields were found
        field_score = min(len([v for v in clean_fields.values() if v is not None]) / 8, 1.0)
        confidence  = round((raw_conf * 0.7) + (field_score * 0.3), 2)

        return DocumentData(
            doc_type=doc_type,
            doc_subtype=subtype,
            fields=clean_fields,
            line_items=items if isinstance(items, list) else [],
            extraction_notes=notes,
        ), confidence

    except Exception:
        return DocumentData(), 0.0
