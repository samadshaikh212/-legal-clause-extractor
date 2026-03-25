import streamlit as st
import pandas as pd
from utils import extract_text_from_pdf, clean_text, chunk_text
from extractor import extract_clauses, summarize_contract

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Legal Clause Extractor",
    page_icon="⚖️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .risk-high   { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:99px; font-size:13px; font-weight:500; }
    .risk-medium { background:#fef3c7; color:#92400e; padding:2px 10px; border-radius:99px; font-size:13px; font-weight:500; }
    .risk-low    { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:99px; font-size:13px; font-weight:500; }
    .risk-none   { background:#f1f5f9; color:#475569; padding:2px 10px; border-radius:99px; font-size:13px; font-weight:500; }
    .clause-card { border:1px solid #e2e8f0; border-radius:10px; padding:16px; margin-bottom:12px; background:#fff; }
    .clause-type { font-size:12px; font-weight:600; color:#6366f1; letter-spacing:.5px; text-transform:uppercase; }
    .clause-summary { font-size:15px; margin:6px 0 4px; color:#1e293b; }
    .clause-parties { font-size:12px; color:#64748b; }
    .exec-summary { background:#f8fafc; border-left:4px solid #6366f1; padding:16px 20px; border-radius:0 8px 8px 0; color:#1e293b; line-height:1.7; }
    [data-testid="stSidebar"] { background:#fafaf9; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ Legal Clause Extractor")
    st.caption("Upload a contract PDF and extract obligations, rights, deadlines, and risk scores — automatically.")
    st.divider()

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="AIza...",
        help="Get a free key at aistudio.google.com"
    )

    st.markdown("**Filters**")
    filter_type = st.multiselect(
        "Clause type",
        ["Obligation", "Right", "Deadline", "Payment", "Termination",
         "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"],
        default=[]
    )
    filter_risk = st.multiselect(
        "Risk level",
        ["High", "Medium", "Low", "None"],
        default=[]
    )

    st.divider()
    st.caption("Built with Streamlit + Gemini 1.5 Flash · Free to deploy on Streamlit Cloud")

# -- Main area --
uploaded_file = st.file_uploader("Drop your contract PDF here", type=["pdf"])

# ADD THIS: Reset session state if a new file is uploaded
if "last_uploaded_file" not in st.session_state:
    st.session_state["last_uploaded_file"] = None

if uploaded_file != st.session_state["last_uploaded_file"]:
    st.session_state["clauses"] = None
    st.session_state["exec_summary"] = None
    st.session_state["last_uploaded_file"] = uploaded_file
    
# ── Main area ─────────────────────────────────────────────────────────────────
st.header("Contract Analysis")

uploaded_file = st.file_uploader(
    "Drop your contract PDF here",
    type=["pdf"],
    help="Supports standard PDF contracts. Max ~50 pages recommended."
)

if not api_key:
    st.info("Enter your Gemini API key in the sidebar to get started.")
    st.stop()

if not uploaded_file:
    st.stop()

# ── Run extraction ────────────────────────────────────────────────────────────
run = st.button("Extract Clauses", type="primary", use_container_width=True)

if run or st.session_state.get("clauses"):

    if run:
        with st.spinner("Reading PDF..."):
            raw_text = extract_text_from_pdf(uploaded_file)
            clean = clean_text(raw_text)
            chunks = chunk_text(clean)

        st.caption(f"Found **{len(chunks)}** paragraphs to analyze.")

        progress_bar = st.progress(0, text="Analyzing clauses...")

        def update_progress(done, total):
            pct = int((done / total) * 100)
            progress_bar.progress(pct, text=f"Analyzing paragraph {done}/{total}...")

        clauses = extract_clauses(chunks, api_key, progress_callback=update_progress)
        progress_bar.empty()

        st.session_state["clauses"] = clauses
        st.session_state["chunk_count"] = len(chunks)

    clauses = st.session_state.get("clauses", [])

    if not clauses:
        st.warning("No legal clauses detected. Try a different PDF.")
        st.stop()

    # ── Apply filters ─────────────────────────────────────────────────────────
    filtered = clauses
    if filter_type:
        filtered = [c for c in filtered if c["clause_type"] in filter_type]
    if filter_risk:
        filtered = [c for c in filtered if c["risk_level"] in filter_risk]

    # ── Stats row ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total clauses", len(clauses))
    col2.metric("High risk", sum(1 for c in clauses if c["risk_level"] == "High"))
    col3.metric("Medium risk", sum(1 for c in clauses if c["risk_level"] == "Medium"))
    col4.metric("Showing", len(filtered))

    st.divider()

    # ── Executive summary ─────────────────────────────────────────────────────
    with st.expander("Executive Summary (AI-generated)", expanded=True):
        if "exec_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                st.session_state["exec_summary"] = summarize_contract(clauses, api_key)
        st.markdown(
            f'<div class="exec-summary">{st.session_state["exec_summary"]}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── View toggle ───────────────────────────────────────────────────────────
    view = st.radio("View as", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

    if view == "Table":
        df = pd.DataFrame([{
            "Type": c["clause_type"],
            "Summary": c["summary"],
            "Risk": c["risk_level"],
            "Risk Reason": c.get("risk_reason", ""),
            "Parties": ", ".join(c.get("key_parties", [])),
        } for c in filtered])

        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            data=csv,
            file_name="clauses.csv",
            mime="text/csv"
        )

    else:
        risk_badge = {
            "High":   '<span class="risk-high">High Risk</span>',
            "Medium": '<span class="risk-medium">Medium Risk</span>',
            "Low":    '<span class="risk-low">Low Risk</span>',
            "None":   '<span class="risk-none">No Risk</span>',
        }

        for clause in filtered:
            risk = clause.get("risk_level", "None")
            badge = risk_badge.get(risk, risk_badge["None"])
            parties = ", ".join(clause.get("key_parties", [])) or "—"
            reason = clause.get("risk_reason", "")

            st.markdown(f"""
            <div class="clause-card">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span class="clause-type">{clause['clause_type']}</span>
                    {badge}
                </div>
                <p class="clause-summary">{clause['summary']}</p>
                <p class="clause-parties">Parties: {parties}{' · ' + reason if reason else ''}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("View original text"):
                st.caption(clause.get("original_text", ""))
