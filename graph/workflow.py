"""LangGraph multi-agent workflow — classify + extract in one VLM call."""

from __future__ import annotations

import uuid
from typing import Optional, TypedDict

from langgraph.graph import END, StateGraph
from PIL import Image

from agents import correction_agent, extraction_agent, validation_agent
from config import AUTO_APPROVE_THRESHOLD, EXTRACTION_CONF_THRESHOLD, MAX_CORRECTION_ATTEMPTS
from database import storage
from models.schemas import ExtractionResult, ProcessingRecord, ValidationResult, ValidationStatus
from pipeline import ingestion, ocr


# ── State ─────────────────────────────────────────────────────────────────────

class InvoiceState(TypedDict):
    document_id:          str
    source_path:          str
    images:               list
    ocr_texts:            list
    extraction:           Optional[ExtractionResult]
    validation:           Optional[ValidationResult]
    correction_attempts:  int
    final_status:         Optional[ValidationStatus]
    processing_notes:     list


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_ingest(state: InvoiceState) -> InvoiceState:
    images = ingestion.load_document(state["source_path"])
    state["images"] = images
    state["processing_notes"].append(f"Ingested {len(images)} page(s)")
    storage.log_event(state["document_id"], "ingested", {"pages": len(images)})
    return state


def node_extract(state: InvoiceState) -> InvoiceState:
    """Combined classify + extract — one VLM call identifies type and reads all fields."""
    combined_ocr = "\n\n".join(state.get("ocr_texts") or [])
    result       = extraction_agent.run(state["images"][0], combined_ocr)
    state["extraction"] = result

    doc = result.extracted_data
    state["processing_notes"].append(
        f"Classified as '{doc.doc_type}' "
        f"({'+ subtype: ' + doc.doc_subtype if doc.doc_subtype else ''}) "
        f"· {len(doc.fields)} fields extracted "
        f"· confidence {result.confidence:.0%}"
    )
    storage.log_event(state["document_id"], "extracted", {
        "doc_type":   doc.doc_type,
        "field_count": len(doc.fields),
        "confidence": result.confidence,
    })
    return state


def node_ocr_fallback(state: InvoiceState) -> InvoiceState:
    """Run Tesseract and merge output to fill gaps from VLM extraction."""
    texts    = [ocr.ocr_extract_text(img) for img in state["images"]]
    combined = "\n\n".join(texts)
    state["ocr_texts"] = texts

    if state["extraction"]:
        merged = ocr.merge_ocr_with_extraction(combined, state["extraction"].extracted_data)
        state["extraction"] = ExtractionResult(
            raw_ocr_text=combined,
            extracted_data=merged,
            confidence=state["extraction"].confidence,
            vlm_response=state["extraction"].vlm_response,
            ocr_used=True,
        )
    state["processing_notes"].append("OCR fallback ran — merged with VLM output")
    storage.log_event(state["document_id"], "ocr_fallback", {"chars": len(combined)})
    return state


def node_validate(state: InvoiceState) -> InvoiceState:
    result = validation_agent.run(state["extraction"])
    state["validation"] = result
    msg = "Validation passed" if result.is_valid else f"Validation failed: {result.failed_fields}"
    state["processing_notes"].append(msg)
    storage.log_event(state["document_id"], "validated", {
        "valid": result.is_valid,
        "failed": result.failed_fields,
    })
    return state


def node_correct(state: InvoiceState) -> InvoiceState:
    state["correction_attempts"] += 1
    updated = correction_agent.run(state["images"][0], state["extraction"], state["validation"])
    state["extraction"] = updated
    state["processing_notes"].append(f"Auto-correction attempt {state['correction_attempts']}")
    storage.log_event(state["document_id"], "corrected", {"attempt": state["correction_attempts"]})
    return state


def node_store(state: InvoiceState) -> InvoiceState:
    v      = state["validation"]
    status = ValidationStatus.VALID if (v and v.is_valid) else ValidationStatus.CORRECTED
    state["final_status"] = status

    ext = state["extraction"]
    storage.save_record(ProcessingRecord(
        document_id=state["document_id"],
        source_path=state["source_path"],
        doc_type=ext.extracted_data.doc_type if ext else "unknown",
        raw_ocr_text="\n\n".join(state.get("ocr_texts") or []),
        vlm_extraction={"fields": ext.extracted_data.fields,
                        "line_items": ext.extracted_data.line_items} if ext else {},
        corrections_applied=[fv.model_dump() for fv in (v.field_validations if v else [])
                             if fv.status == ValidationStatus.CORRECTED],
        final_data={"doc_type": ext.extracted_data.doc_type,
                    "doc_subtype": ext.extracted_data.doc_subtype,
                    "fields": ext.extracted_data.fields,
                    "line_items": ext.extracted_data.line_items,
                    "extraction_notes": ext.extracted_data.extraction_notes} if ext else {},
        validation_status=status,
        extraction_confidence=ext.confidence if ext else 0.0,
        processing_notes=state["processing_notes"],
    ))
    storage.log_event(state["document_id"], "stored", {"status": status.value})
    return state


def node_review_queue(state: InvoiceState) -> InvoiceState:
    state["final_status"] = ValidationStatus.PENDING
    ext  = state["extraction"]
    notes = state["processing_notes"] + ["Sent to human review queue"]

    storage.save_record(ProcessingRecord(
        document_id=state["document_id"],
        source_path=state["source_path"],
        doc_type=ext.extracted_data.doc_type if ext else "unknown",
        raw_ocr_text="\n\n".join(state.get("ocr_texts") or []),
        vlm_extraction={"fields": ext.extracted_data.fields,
                        "line_items": ext.extracted_data.line_items} if ext else {},
        corrections_applied=[],
        final_data={"doc_type": ext.extracted_data.doc_type,
                    "fields": ext.extracted_data.fields,
                    "line_items": ext.extracted_data.line_items} if ext else {},
        validation_status=ValidationStatus.PENDING,
        extraction_confidence=ext.confidence if ext else 0.0,
        processing_notes=notes,
    ))
    storage.log_event(state["document_id"], "review_queue", {"reason": "low confidence or max corrections"})
    return state


# ── Routers ───────────────────────────────────────────────────────────────────

def _should_run_ocr(state: InvoiceState) -> str:
    conf = state["extraction"].confidence if state["extraction"] else 0.0
    return "ocr_fallback" if conf < EXTRACTION_CONF_THRESHOLD else "validate"


def _route_after_validation(state: InvoiceState) -> str:
    v    = state["validation"]
    conf = state["extraction"].confidence if state["extraction"] else 0.0

    if v and not v.is_valid:
        if state["correction_attempts"] < MAX_CORRECTION_ATTEMPTS:
            return "correct"
        return "review_queue"

    return "store" if conf >= AUTO_APPROVE_THRESHOLD else "review_queue"


# ── Build & run ───────────────────────────────────────────────────────────────

def build_graph():
    storage.init_db()
    g = StateGraph(InvoiceState)

    g.add_node("ingest",       node_ingest)
    g.add_node("extract",      node_extract)
    g.add_node("ocr_fallback", node_ocr_fallback)
    g.add_node("validate",     node_validate)
    g.add_node("correct",      node_correct)
    g.add_node("store",        node_store)
    g.add_node("review_queue", node_review_queue)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "extract")
    g.add_conditional_edges("extract", _should_run_ocr,
                             {"ocr_fallback": "ocr_fallback", "validate": "validate"})
    g.add_edge("ocr_fallback", "validate")
    g.add_conditional_edges("validate", _route_after_validation,
                             {"correct": "correct", "store": "store", "review_queue": "review_queue"})
    g.add_edge("correct",      "validate")
    g.add_edge("store",        END)
    g.add_edge("review_queue", END)

    return g.compile()


def _initial_state(path: str) -> InvoiceState:
    return {
        "document_id":         str(uuid.uuid4()),
        "source_path":         str(path),
        "images":              [],
        "ocr_texts":           [],
        "extraction":          None,
        "validation":          None,
        "correction_attempts": 0,
        "final_status":        None,
        "processing_notes":    [],
    }


def process_document(path: str) -> InvoiceState:
    """Run the full pipeline and return the final state (blocking)."""
    return build_graph().invoke(_initial_state(path))


def process_document_stream(path: str):
    """Stream pipeline events in real time.

    Yields (node_name: str, state: InvoiceState) after each node completes.
    Use this for progressive UI updates.
    """
    graph = build_graph()
    final_state: InvoiceState = _initial_state(path)

    for chunk in graph.stream(final_state):
        # chunk = {node_name: updated_state_dict}
        node_name   = list(chunk.keys())[0]
        final_state = chunk[node_name]
        yield node_name, final_state
