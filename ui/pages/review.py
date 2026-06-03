"""Review Queue — human approval for low-confidence / failed documents."""

from __future__ import annotations

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.getcwd())

from ui.styles import badge, page_header


def _load_pending() -> list[dict]:
    try:
        from database.storage import get_pending_review
        return get_pending_review(limit=100)
    except Exception:
        return []


def render() -> None:
    page_header("👁️", "Review Queue", "Documents flagged for human verification")

    pending_records = _load_pending()

    # ── Stats ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending Review",        len(pending_records))
    c2.metric("Approved (this session)", len(st.session_state.get("approved_ids", set())))
    c3.metric("Rejected (this session)", len(st.session_state.get("rejected_ids",  set())))

    if "approved_ids" not in st.session_state:
        st.session_state.approved_ids = set()
    if "rejected_ids" not in st.session_state:
        st.session_state.rejected_ids = set()

    # Filter out already actioned
    pending = [
        r for r in pending_records
        if r["document_id"] not in st.session_state.approved_ids
        and r["document_id"] not in st.session_state.rejected_ids
    ]

    st.markdown("<br/>", unsafe_allow_html=True)

    if not pending:
        st.success("Review queue is empty — all documents have been actioned.")
        return

    for doc in pending:
        doc_id   = doc["document_id"]
        fname    = (doc.get("source_path") or "").split("/")[-1] or doc_id[:12]
        conf     = doc.get("extraction_confidence", 0.0)
        doc_type = (doc.get("doc_type") or "invoice").title()
        notes    = json.loads(doc.get("processing_notes") or "[]")
        final    = json.loads(doc.get("final_data")       or "{}")

        reason = next(
            (n for n in reversed(notes) if "review" in n.lower() or "confidence" in n.lower()),
            "Low confidence or validation failed",
        )

        with st.expander(
            f"🔍  {fname}  ·  {doc_type}  ·  Confidence {conf*100:.0f}%  ·  {reason}",
            expanded=False,
        ):
            left, right = st.columns([2, 1])

            with left:
                st.markdown("**Review & Edit Extracted Fields**")
                edited = {}
                display_keys = ["invoice_number","vendor_name","invoice_date","due_date",
                                 "total_amount","tax_amount","subtotal","currency","iban","payment_terms"]
                for k in display_keys:
                    v = final.get(k)
                    edited[k] = st.text_input(
                        k.replace("_", " ").title(),
                        value=str(v) if v is not None else "",
                        key=f"{doc_id}_{k}",
                    )

            with right:
                st.markdown("**Summary**")
                st.markdown(f"- **Doc ID:** `{doc_id[:8]}`")
                st.markdown(f"- **Type:** {doc_type}")
                st.markdown(
                    f"- **Confidence:** "
                    f"<span style='color:{'#d97706' if conf>=0.5 else '#dc2626'};font-weight:700'>"
                    f"{conf*100:.0f}%</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"- **Reason flagged:** {reason}")
                st.markdown("**Processing log:**")
                for note in notes[-4:]:
                    st.caption(f"• {note}")

                st.markdown("<br/>", unsafe_allow_html=True)
                col_a, col_r = st.columns(2)

                with col_a:
                    if st.button("✅ Approve", key=f"approve_{doc_id}",
                                 use_container_width=True, type="primary"):
                        try:
                            from database.storage import approve_record
                            # Convert edited strings back to typed values
                            clean = {}
                            for k, v in edited.items():
                                if v.strip() == "" or v == "None":
                                    clean[k] = None
                                elif k in ("total_amount","tax_amount","subtotal"):
                                    try:
                                        clean[k] = float(v.replace(",","").replace("$",""))
                                    except ValueError:
                                        clean[k] = None
                                else:
                                    clean[k] = v.strip()
                            approve_record(doc_id, clean)
                            st.session_state.approved_ids.add(doc_id)
                            st.toast(f"Document {doc_id[:8]} approved.", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not approve: {e}")

                with col_r:
                    if st.button("❌ Reject", key=f"reject_{doc_id}", use_container_width=True):
                        try:
                            from database.storage import reject_record
                            reject_record(doc_id)
                            st.session_state.rejected_ids.add(doc_id)
                            st.toast(f"Document {doc_id[:8]} rejected.", icon="🗑️")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not reject: {e}")
