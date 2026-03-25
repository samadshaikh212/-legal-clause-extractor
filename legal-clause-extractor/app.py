import streamlit as st
import pandas as pd
from utils import extract_text_from_pdf, clean_text, chunk_text
from extractor import extract_clauses, summarize_contract

st.set_page_config(page_title="Legal Clause Extractor", page_icon="⚖️", layout="wide")

# (Keep your existing .risk-high, .clause-card CSS here...)
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
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚖️ Legal Clause Extractor")
    # Tip: You can put your key in Streamlit Secrets to avoid pasting it every time
    api_key = st.text_input("Gemini API Key", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    
    st.markdown("**Filters**")
    filter_type = st.multiselect("Clause type", ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"])
    filter_risk = st.multiselect("Risk level", ["High", "Medium", "Low", "None"])

st.header("Contract Analysis")
uploaded_file = st.file_uploader("Drop your contract PDF here", type=["pdf"])

# SESSION RESET: Clear old data if a new file is uploaded
if "last_file" not in st.session_state: st.session_state.last_file = None
if uploaded_file != st.session_state.last_file:
    st.session_state.clauses = None
    st.session_state.exec_summary = None
    st.session_state.last_file = uploaded_file

if not api_key:
    st.info("Please enter your API key in the sidebar.")
    st.stop()

if uploaded_file:
    if st.button("Extract Clauses", type="primary", use_container_width=True):
        with st.spinner("Processing PDF..."):
            raw_text = extract_text_from_pdf(uploaded_file)
            chunks = chunk_text(clean_text(raw_text))
            
            progress_bar = st.progress(0)
            def update_p(done, total):
                progress_bar.progress(done/total, text=f"Analyzing {done}/{total}")
            
            st.session_state.clauses = extract_clauses(chunks, api_key, update_p)
            progress_bar.empty()

    if st.session_state.get("clauses"):
        clauses = st.session_state.clauses
        
        # Filtering logic
        filtered = [c for c in clauses if (not filter_type or c["clause_type"] in filter_type) and (not filter_risk or c["risk_level"] in filter_risk)]

        # Stats
        cols = st.columns(4)
        cols[0].metric("Total", len(clauses))
        cols[1].metric("High Risk", sum(1 for c in clauses if c["risk_level"] == "High"))
        cols[3].metric("Showing", len(filtered))

        # Executive Summary
        with st.expander("AI Executive Summary", expanded=True):
            if not st.session_state.get("exec_summary"):
                st.session_state.exec_summary = summarize_contract(clauses, api_key)
            st.markdown(f'<div class="exec-summary">{st.session_state.exec_summary}</div>', unsafe_allow_html=True)

        # Display Cards
        for c in filtered:
            risk = c.get("risk_level", "None")
            badge = f'<span class="risk-{risk.lower()}">{risk} Risk</span>'
            st.markdown(f"""
                <div class="clause-card">
                    <div style="display:flex;justify-content:space-between;">
                        <span class="clause-type">{c['clause_type']}</span>{badge}
                    </div>
                    <p class="clause-summary">{c['summary']}</p>
                    <p class="clause-parties">Parties: {", ".join(c.get("key_parties", []))} | {c.get("risk_reason", "")}</p>
                </div>
            """, unsafe_allow_html=True)
            with st.expander("View Original Text"):
                st.write(c.get("original_text", "Text not available"))
    elif st.session_state.last_file:
        st.warning("No legal clauses detected. Ensure the PDF contains readable text.")
