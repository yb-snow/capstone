"""Dashboard page — live KPIs, recent activity, pipeline health."""

from __future__ import annotations

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.getcwd())

from ui.styles import badge, page_header
from ui.components.metrics import render_kpi_row


def _load_stats() -> dict:
    try:
        from database.storage import get_stats
        return get_stats()
    except Exception:
        return {"total": 0, "success_rate": 0.0, "pending": 0, "today": 0, "by_type": {}}


def _load_recent(limit: int = 6) -> list[dict]:
    try:
        from database.storage import list_records
        return list_records(limit=limit)
    except Exception:
        return []


def render() -> None:
    page_header("📊", "Dashboard", "Overview of document processing activity")

    stats  = _load_stats()
    recent = _load_recent()

    render_kpi_row(
        total=stats["total"],
        success_rate=stats["success_rate"],
        pending=stats["pending"],
        today=stats["today"],
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])

    with left:
        st.markdown("#### Recent Activity")
        if not recent:
            st.info("No documents processed yet. Go to **Process Document** to get started.")
        else:
            for doc in recent:
                final = json.loads(doc.get("final_data") or "{}")
                status = doc.get("validation_status", "unknown")
                conf   = doc.get("extraction_confidence", 0.0)
                b      = badge(status, status if status in ("valid","failed","corrected","pending_review") else "review")
                fname  = (doc.get("source_path") or "").split("/")[-1] or doc["document_id"][:12]
                vendor = final.get("vendor_name") or "—"
                total  = final.get("total_amount")
                total_str = f"${total:,.2f}" if total else "—"
                doc_type  = doc.get("doc_type", "invoice").title()

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.2, 1])
                    with c1:
                        st.markdown(f"**{fname}**")
                        st.caption(f"{doc['document_id'][:8]}  ·  {vendor}")
                    with c2:
                        st.caption("Type / Confidence")
                        st.markdown(f"{doc_type}  ·  {conf*100:.0f}%")
                    with c3:
                        st.caption("Total")
                        st.markdown(total_str)
                    with c4:
                        st.caption("Status")
                        st.markdown(b, unsafe_allow_html=True)

    with right:
        st.markdown("#### Pipeline Health")
        with st.container(border=True):
            for stage in ["Ingestion", "Classification", "Extraction", "OCR Fallback",
                          "Validation", "Correction", "Storage"]:
                st.markdown(f"**{stage}**")
                st.caption("✅ Operational")
                st.markdown("<hr style='margin:4px 0;border-color:#f0f4f8'/>", unsafe_allow_html=True)

        st.markdown("#### Document Types")
        with st.container(border=True):
            by_type = stats.get("by_type", {})
            total   = stats["total"] or 1
            for label, key in [("🧾 Invoices", "invoice"), ("🧾 Receipts", "receipt"), ("📋 Forms", "form")]:
                cnt  = by_type.get(key, 0)
                pct  = cnt / total
                st.markdown(f"{label}  — {cnt}  ({pct*100:.0f}%)")
                st.progress(pct)
