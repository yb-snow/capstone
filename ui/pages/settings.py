import streamlit as st
from ui.styles import page_header


def render() -> None:
    page_header("⚙️", "Settings", "Configure the pipeline, VLM backend, and thresholds")

    tab_vlm, tab_thresholds, tab_vendors, tab_about = st.tabs(
        ["🤖 VLM Backend", "🎚️ Thresholds", "🏢 Vendors", "ℹ️ About"]
    )

    # ── VLM Backend ───────────────────────────────────────────
    with tab_vlm:
        st.markdown("#### Vision-Language Model")
        backend = st.selectbox(
            "VLM Backend",
            [
                "gemini (Free — Google account only, recommended)",
                "claude (Paid — Anthropic API key required)",
                "internvl (Local GPU — no API key)",
                "llava (Local GPU — no API key)",
            ],
            index=0,
        )

        if "gemini" in backend:
            st.info("Gemini API is **free** — get your key at [aistudio.google.com](https://aistudio.google.com/app/apikey). No credit card required.")
            st.text_input(
                "Gemini API Key",
                type="password",
                placeholder="AIza…",
                help="Get your free key at aistudio.google.com",
            )
            st.selectbox(
                "Gemini Model",
                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
                index=0,
            )
        elif "claude" in backend:
            st.text_input(
                "Anthropic API Key",
                type="password",
                placeholder="sk-ant-…",
                help="Get your key at console.anthropic.com",
            )
            st.selectbox(
                "Claude Model",
                ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
                index=0,
            )
        else:
            st.text_input("Local Model Path / HuggingFace ID", placeholder="InternVL2-8B")
            st.selectbox("Device", ["cuda", "cpu", "mps"])

        st.markdown("#### OCR (Tesseract)")
        st.text_input("Tesseract Binary Path", placeholder="/usr/bin/tesseract")
        st.number_input("Scan DPI", min_value=150, max_value=600, value=300, step=50)

        if st.button("💾 Save VLM Settings", type="primary"):
            st.success("Settings saved (prototype — no persistence yet).")

    # ── Thresholds ────────────────────────────────────────────
    with tab_thresholds:
        st.markdown("#### Confidence Thresholds")
        st.markdown(
            "Documents below **Extraction Threshold** will trigger the OCR fallback.  \n"
            "Documents below **Auto-Approve Threshold** will be sent to the Review Queue."
        )

        ext_thresh = st.slider(
            "Extraction Confidence Threshold",
            min_value=0.0, max_value=1.0, value=0.70, step=0.05,
            format="%.2f",
            help="Below this score, OCR fallback is triggered.",
        )
        approve_thresh = st.slider(
            "Auto-Approve Threshold",
            min_value=0.0, max_value=1.0, value=0.85, step=0.05,
            format="%.2f",
            help="Below this score, document goes to Human Review Queue.",
        )

        st.markdown("#### Validation Rules")
        total_tol = st.number_input(
            "Total Reconciliation Tolerance ($)",
            min_value=0.0, max_value=1.0, value=0.01, step=0.01, format="%.2f",
        )
        fuzzy_thresh = st.slider(
            "Vendor Fuzzy Match Threshold (rapidfuzz score)",
            min_value=0, max_value=100, value=80,
            help="Minimum score for a vendor name to be considered a match.",
        )
        max_corrections = st.number_input(
            "Max Auto-Correction Attempts",
            min_value=1, max_value=5, value=2,
        )

        if st.button("💾 Save Threshold Settings", type="primary"):
            st.success("Thresholds saved (prototype — no persistence yet).")

    # ── Vendors ───────────────────────────────────────────────
    with tab_vendors:
        st.markdown("#### Known Vendor Registry (ChromaDB)")
        st.markdown(
            "Vendors listed here are used for fuzzy semantic matching during validation. "
            "Add your organisation's known vendors to improve match accuracy."
        )

        vendor_list = st.text_area(
            "Known Vendors (one per line)",
            value="\n".join([
                "Acme Corp", "Global Supplies Inc", "Tech Solutions Ltd",
                "Office Depot", "Amazon Business", "Staples", "Dell Technologies",
            ]),
            height=180,
        )
        if st.button("➕ Update Vendor Registry", type="primary"):
            vendors = [v.strip() for v in vendor_list.splitlines() if v.strip()]
            st.success(f"{len(vendors)} vendor(s) staged for ChromaDB. Connect backend to persist.")

    # ── About ─────────────────────────────────────────────────
    with tab_about:
        st.markdown("#### System Information")
        info = {
            "Application": "Doc Agent — Multi-Modal Document Intelligence Agent",
            "Version":     "0.1.0 (skeleton)",
            "Orchestration": "LangGraph",
            "VLM Backend": "claude-sonnet-4-6",
            "OCR Engine":  "Tesseract",
            "Storage":     "SQLite",
            "Vector DB":   "ChromaDB",
            "UI":          "Streamlit",
        }
        for k, v in info.items():
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"**{k}**")
            with c2:
                st.markdown(v)
