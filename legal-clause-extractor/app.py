import streamlit as st
import pandas as pd
from utils import extract_text_from_pdf, clean_text, chunk_text
from extractor import extract_clauses, summarize_contract

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Legal Clause Extractor",
    page_icon="⚖️",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .risk-High   { background:#fee2e2; color:#991b1b; padding:3px 12px; border-radius:99px; font-size:12px; font-weight:600; }
    .risk-Medium { background:#fef3c7; color:#92400e; padding:3px 12px; border-radius:99px; font-size:12px; font-weight:600; }
    .risk-Low    { background:#dcfce7; color:#166534; padding:3px 12px; border-radius:99px; font-size:12px; font-weight:600; }
    .risk-None   { background:#f1f5f9; color:#475569; padding:3px 12px; border-radius:99px; font-size:12px; font-weight:600; }

    .clause-card {
        border: 0.5px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
        background: #ffffff;
    }
    .clause-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .clause-type {
        font-size: 11px;
        font-weight: 700;
        color: #6366f1;
        letter-spacing: .7px;
        text-transform: uppercase;
    }
    .clause-summary {
        font-size: 15px;
        color: #1e293b;
        margin: 6px 0 6px;
        line-height: 1.5;
    }
    .clause-meta {
        font-size: 12px;
        color: #94a3b8;
    }
    .exec-box {
        background: #f8fafc;
        border-left: 4px solid #6366f1;
        padding: 16px 20px;
        border-radius: 0 10px 10px 0;
        font-size: 15px;
        color: #1e293b;
        line-height: 1.8;
        margin-bottom: 1rem;
    }
    .stat-label { font-size: 12px; color: #94a3b8; margin-bottom: 2px; }
    .stat-value { font-size: 26px; font-weight: 600; color: #1e293b; }

    [data-testid="stSidebar"] { background: #fafaf9; }
    .stButton>button { border-radius: 8px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚖️ Legal Clause Extractor")
    st.caption("AI-powered contract analysis using Llama 3 on Groq.")
    st.divider()

    api_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Free at console.groq.com — no credit card needed"
    )

    if not api_key:
        st.warning("Paste your Groq API key above to begin.")

    st.divider()
    st.markdown("**Filter results**")

    filter_type = st.multiselect(
        "Clause type",
        ["Obligation", "Right", "Deadline", "Payment", "Termination",
         "Confidentiality", "Liability", "Indemnity", "Governing Law",
         "Dispute Resolution", "Warranty", "Intellectual Property", "Other"],
        default=[]
    )
    filter_risk = st.multiselect(
        "Risk level",
        ["High", "Medium", "Low", "None"],
        default=[]
    )

    st.divider()

    if st.session_state.get("clauses"):
        if st.button("Clear results", use_container_width=True):
            st.session_state.clauses = []
            st.session_state.exec_summary = ""
            st.rerun()

    st.caption("Built with Streamlit · Groq · Llama 3 70B · PyMuPDF")


# ── Main ──────────────────────────────────────────────────────────────────────
st.header("Contract Analysis")

uploaded_file = st.file_uploader(
    "Drop your contract PDF here",
    type=["pdf"],
    help="Works best on text-based PDFs. Scanned image PDFs may give poor results."
)

# Guard: need both file and key
if not api_key:
    st.info("Enter your Groq API key in the sidebar to get started.")
    st.stop()

if not uploaded_file:
    st.stop()

# ── Run analysis ──────────────────────────────────────────────────────────────
if st.button("Extract Clauses", type="primary", use_container_width=True):
    # Clear previous run
    st.session_state.clauses = []
    st.session_state.exec_summary = ""

    with st.spinner("Reading PDF..."):
        raw_text = extract_text_from_pdf(uploaded_file)
        cleaned  = clean_text(raw_text)
        chunks   = chunk_text(cleaned)

    if not chunks:
        st.error("No text found in this PDF. It may be a scanned image — try a text-based PDF.")
        st.stop()

    st.info(f"Found **{len(chunks)}** paragraphs. Running AI analysis...")

    progress_bar = st.progress(0, text="Starting...")

    def update_progress(done: int, total: int):
        pct  = int((done / total) * 100)
        progress_bar.progress(pct, text=f"Analyzing paragraph {done} of {total}...")

    clauses = extract_clauses(chunks, api_key, progress_callback=update_progress)
    progress_bar.empty()

    if not clauses:
        st.error(
            "No legal clauses detected. Possible reasons:\n"
            "- Wrong API key\n"
            "- PDF is a scanned image (no text layer)\n"
            "- Document has no standard legal clause structure"
        )
        st.stop()

    st.session_state.clauses = clauses

    with st.spinner("Generating executive summary..."):
        st.session_state.exec_summary = summarize_contract(clauses, api_key)

    st.success(f"Done! Extracted **{len(clauses)}** clauses.")
    st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
clauses = st.session_state.get("clauses", [])

if not clauses:
    st.stop()

# Apply filters
filtered = clauses
if filter_type:
    filtered = [c for c in filtered if c.get("clause_type") in filter_type]
if filter_risk:
    filtered = [c for c in filtered if c.get("risk_level") in filter_risk]

# ── Stats row ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown('<div class="stat-label">Total clauses</div>'
                f'<div class="stat-value">{len(clauses)}</div>', unsafe_allow_html=True)
with c2:
    high = sum(1 for c in clauses if c.get("risk_level") == "High")
    st.markdown('<div class="stat-label">High risk</div>'
                f'<div class="stat-value" style="color:#991b1b">{high}</div>', unsafe_allow_html=True)
with c3:
    med = sum(1 for c in clauses if c.get("risk_level") == "Medium")
    st.markdown('<div class="stat-label">Medium risk</div>'
                f'<div class="stat-value" style="color:#92400e">{med}</div>', unsafe_allow_html=True)
with c4:
    low = sum(1 for c in clauses if c.get("risk_level") == "Low")
    st.markdown('<div class="stat-label">Low risk</div>'
                f'<div class="stat-value" style="color:#166534">{low}</div>', unsafe_allow_html=True)
with c5:
    st.markdown('<div class="stat-label">Showing</div>'
                f'<div class="stat-value">{len(filtered)}</div>', unsafe_allow_html=True)

st.divider()

# ── Executive summary ─────────────────────────────────────────────────────────
summary_text = st.session_state.get("exec_summary", "")
if summary_text:
    with st.expander("Executive Summary", expanded=True):
        st.markdown(
            f'<div class="exec-box">{summary_text}</div>',
            unsafe_allow_html=True
        )

# ── View toggle + export ──────────────────────────────────────────────────────
col_view, col_export = st.columns([3, 1])

with col_view:
    view = st.radio("View as", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

with col_export:
    if filtered:
        df_export = pd.DataFrame([{
            "Type":        c.get("clause_type", ""),
            "Summary":     c.get("summary", ""),
            "Risk":        c.get("risk_level", ""),
            "Risk Reason": c.get("risk_reason", ""),
            "Parties":     ", ".join(c.get("key_parties", [])),
            "Obligations": "; ".join(c.get("obligations", [])),
            "Rights":      "; ".join(c.get("rights", [])),
        } for c in filtered])
        st.download_button(
            "Download CSV",
            data=df_export.to_csv(index=False),
            file_name="clauses.csv",
            mime="text/csv",
            use_container_width=True
        )

st.divider()

# ── No results after filter ───────────────────────────────────────────────────
if not filtered:
    st.warning("No clauses match the selected filters. Try clearing the filters in the sidebar.")
    st.stop()

# ── Table view ────────────────────────────────────────────────────────────────
if view == "Table":
    df = pd.DataFrame([{
        "Type":    c.get("clause_type", ""),
        "Summary": c.get("summary", ""),
        "Risk":    c.get("risk_level", ""),
        "Reason":  c.get("risk_reason", ""),
        "Parties": ", ".join(c.get("key_parties", [])),
    } for c in filtered])
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── Card view ─────────────────────────────────────────────────────────────────
else:
    for clause in filtered:
        risk      = clause.get("risk_level", "None")
        ctype     = clause.get("clause_type", "Other")
        summary   = clause.get("summary", "")
        reason    = clause.get("risk_reason", "")
        parties   = ", ".join(clause.get("key_parties", [])) or "—"
        obls      = clause.get("obligations", [])
        rights    = clause.get("rights", [])

        st.markdown(f"""
        <div class="clause-card">
            <div class="clause-header">
                <span class="clause-type">{ctype}</span>
                <span class="risk-{risk}">{risk} Risk</span>
            </div>
            <div class="clause-summary">{summary}</div>
            <div class="clause-meta">Parties: {parties}{(" · " + reason) if reason else ""}</div>
        </div>
        """, unsafe_allow_html=True)

        # Show obligations / rights if present
        if obls or rights:
            with st.expander("Details"):
                if obls:
                    st.markdown("**Obligations**")
                    for o in obls:
                        st.markdown(f"- {o}")
                if rights:
                    st.markdown("**Rights**")
                    for r in rights:
                        st.markdown(f"- {r}")
                st.caption("Original text:")
                st.caption(clause.get("original_text", ""))
        else:
            with st.expander("Original text"):
                st.caption(clause.get("original_text", ""))
