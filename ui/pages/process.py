"""Process Document page — upload, run real pipeline, display all extracted fields."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

from ui.styles import badge, page_header
from ui.components import pipeline_status
from ui.components.field_groups import format_value, group_fields, pretty_label

sys.path.insert(0, os.getcwd())

_DOC_TYPE_ICONS = {
    "invoice":        "🧾",
    "receipt":        "🧾",
    "purchase_order": "📦",
    "bank_statement": "🏦",
    "expense_report": "💸",
    "quote":          "💬",
    "delivery_note":  "🚚",
    "contract":       "📜",
    "form":           "📋",
    "other":          "📄",
    "unknown":        "❓",
}


def _run_pipeline(uploaded_file, placeholder) -> dict:
    """Run the real LangGraph pipeline and update the stepper after EACH node completes."""
    from graph.workflow import process_document_stream
    from ui.components.pipeline_status import render_progress

    # Save upload to a temp file
    suffix = Path(uploaded_file.name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    completed_nodes: set = set()
    final_state           = None
    skipped_nodes:  set = set()

    # Node display labels for the status caption
    _labels = {
        "ingest":       "📥 Ingesting document…",
        "extract":      "🔍 Classifying and extracting fields with AI…",
        "ocr_fallback": "📄 Running OCR fallback (low confidence detected)…",
        "validate":     "✅ Validating extracted data…",
        "correct":      "🔄 Auto-correcting failed fields…",
        "store":        "💾 Saving to database…",
        "review_queue": "👁️ Routing to human review queue…",
    }

    try:
        for node_name, state in process_document_stream(tmp_path):
            # Mark this node as done
            completed_nodes.add(node_name)
            final_state = state

            # Detect skipped OCR (if we jump straight from extract to validate)
            if node_name == "validate" and "ocr_fallback" not in completed_nodes:
                skipped_nodes.add("ocr_fallback")

            # Render the stepper with REAL progress
            with placeholder.container():
                render_progress(completed_nodes, skipped_nodes=skipped_nodes)
                label = _labels.get(node_name, f"Running {node_name}…")
                notes = state.get("processing_notes") or []
                last_note = notes[-1] if notes else ""
                st.caption(f"✓ {label}  " + (f"· _{last_note}_" if last_note else ""))

    finally:
        os.unlink(tmp_path)

    if final_state is None:
        raise RuntimeError("Pipeline produced no output.")

    ext = final_state.get("extraction")
    val = final_state.get("validation")
    doc = ext.extracted_data if ext else None

    validation_details = []
    if val:
        for fv in val.field_validations:
            validation_details.append({
                "Field":   fv.field,
                "Status":  fv.status.value,
                "Message": fv.message or "",
            })

    return {
        "doc_type":              doc.doc_type         if doc else "unknown",
        "doc_subtype":           doc.doc_subtype       if doc else None,
        "fields":                doc.fields            if doc else {},
        "line_items":            doc.line_items        if doc else [],
        "extraction_notes":      doc.extraction_notes  if doc else "",
        "extraction_confidence": ext.confidence        if ext else 0.0,
        "ocr_used":              ext.ocr_used          if ext else False,
        "validation_status":     final_state["final_status"].value
                                 if final_state.get("final_status") else "unknown",
        "corrections":           final_state.get("correction_attempts", 0),
        "validation_details":    validation_details,
        "document_id":           final_state.get("document_id", ""),
        "processing_notes":      final_state.get("processing_notes", []),
        "skipped_nodes":         skipped_nodes,
    }


def _show_results(result: dict) -> None:
    st.markdown("<br/>", unsafe_allow_html=True)

    doc_type = result["doc_type"]
    icon     = _DOC_TYPE_ICONS.get(doc_type, "📄")
    subtype  = f" · {result['doc_subtype']}" if result.get("doc_subtype") else ""
    status   = result["validation_status"]
    conf     = result["extraction_confidence"]
    ocr_note = "OCR fallback used" if result["ocr_used"] else "OCR skipped (high confidence)"

    # ── Summary banner ────────────────────────────────────────────────────────
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Document Type",   f"{icon} {doc_type.replace('_',' ').title()}{subtype}")
        c2.metric("Confidence",      f"{conf*100:.0f}%")
        c3.metric("Fields Found",    len(result["fields"]))
        c4.metric("Status",          status.replace("_"," ").title())

    if result.get("extraction_notes"):
        st.info(f"**AI summary:** {result['extraction_notes']}")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_fields, tab_items, tab_validation, tab_log, tab_export = st.tabs([
        "📋 Extracted Fields",
        f"🗒️ Line Items ({len(result['line_items'])})",
        "✅ Validation",
        "📜 Pipeline Log",
        "⬇️ Export",
    ])

    # ── Fields tab: grouped display ───────────────────────────────────────────
    with tab_fields:
        groups = group_fields(result["fields"])

        if not groups:
            st.warning("No fields were extracted. Try a clearer image.")
        else:
            for group_label, group_fields_dict in groups.items():
                st.markdown(f"**{group_label}**")
                cols = st.columns(2)
                for i, (key, val) in enumerate(group_fields_dict.items()):
                    cols[i % 2].text_input(
                        pretty_label(key),
                        value=format_value(key, val),
                        disabled=True,
                        key=f"field_{result['document_id']}_{key}",
                    )
                st.markdown("<hr style='margin:8px 0;border-color:#e2e8f0'/>",
                            unsafe_allow_html=True)

    # ── Line items tab ────────────────────────────────────────────────────────
    with tab_items:
        items = result.get("line_items") or []
        if items:
            import pandas as pd
            # Normalise: each item may have different keys
            df = pd.DataFrame(items)
            # Rename columns to Title Case
            df.columns = [pretty_label(c) for c in df.columns]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(items)} line item(s) extracted")
        else:
            st.info("No line items / table data found in this document.")

    # ── Validation tab ────────────────────────────────────────────────────────
    with tab_validation:
        b = badge(status, status)
        st.markdown(
            f"**Status:** {b} &nbsp;&nbsp; **Corrections applied:** {result['corrections']} &nbsp;&nbsp; {ocr_note}",
            unsafe_allow_html=True,
        )
        if result["validation_details"]:
            import pandas as pd
            st.dataframe(
                pd.DataFrame(result["validation_details"]),
                use_container_width=True, hide_index=True,
            )

    # ── Log tab ───────────────────────────────────────────────────────────────
    with tab_log:
        for note in result.get("processing_notes", []):
            st.markdown(f"- {note}")

    # ── Export tab ────────────────────────────────────────────────────────────
    with tab_export:
        import pandas as pd

        export_data = {
            "doc_type":   result["doc_type"],
            "doc_subtype":result.get("doc_subtype"),
            **result["fields"],
        }
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(export_data, indent=2, default=str),
                file_name=f"extracted_{result['document_id'][:8]}.json",
                mime="application/json",
                use_container_width=True,
            )
        with c2:
            flat = {k: v for k, v in export_data.items() if not isinstance(v, list)}
            st.download_button(
                "⬇️ Download CSV",
                data=pd.DataFrame([flat]).to_csv(index=False),
                file_name=f"extracted_{result['document_id'][:8]}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        if result["line_items"]:
            st.download_button(
                "⬇️ Line Items CSV",
                data=pd.DataFrame(result["line_items"]).to_csv(index=False),
                file_name=f"line_items_{result['document_id'][:8]}.csv",
                mime="text/csv",
                use_container_width=True,
            )


def render() -> None:
    page_header("🔄", "Process Document",
                "Upload any invoice, receipt, form, or document — AI auto-detects type and extracts all fields")

    if "process_result"  not in st.session_state:
        st.session_state.process_result  = None

    uploaded = st.file_uploader(
        "Drop a file here or click to browse",
        type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
        help="Supported: PDF, PNG, JPG, TIFF, BMP  ·  Max 200 MB",
        key="doc_upload",
    )

    if uploaded:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"**Uploaded:** `{uploaded.name}`  ({uploaded.size // 1024} KB)")
        with c2:
            run = st.button("▶  Run Pipeline", type="primary", use_container_width=True)

        if run:
            st.session_state.process_result = None
            placeholder = st.empty()
            with st.spinner("Processing…"):
                try:
                    st.session_state.process_result = _run_pipeline(uploaded, placeholder)
                except Exception as e:
                    err = str(e)
                    if "429" in err or "RESOURCE_EXHAUSTED" in err:
                        st.error("Gemini rate limit — wait 60 seconds and try again.")
                    elif "poppler" in err.lower() or "page count" in err.lower():
                        st.error("Poppler not found. Run: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)")
                    elif "tesseract" in err.lower():
                        st.error("Tesseract not found. Run: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Linux)")
                    else:
                        st.error(f"Pipeline error: {e}")
            placeholder.empty()

    elif st.session_state.process_result is None:
        st.markdown("<br/>", unsafe_allow_html=True)
        with st.container(border=True):
            pipeline_status.render()
            st.caption("Pipeline ready — upload any document to begin.")

    if st.session_state.process_result:
        pipeline_status.render()
        status = st.session_state.process_result["validation_status"]
        if status in ("valid", "corrected"):
            st.success("Document processed successfully.")
        elif status == "pending_review":
            st.warning("Document sent to Review Queue — confidence below auto-approve threshold.")
        else:
            st.error("Processing completed with errors.")
        _show_results(st.session_state.process_result)
