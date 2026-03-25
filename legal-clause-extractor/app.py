import streamlit as st
import pandas as pd
from utils import extract_text_from_pdf, clean_text, chunk_text
from extractor import extract_clauses, summarize_contract

st.set_page_config(page_title="Legal Clause Extractor", layout="wide")

# CSS (kept the same for brevity)
st.markdown("<style>.risk-high {background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:99px;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚖️ Legal Extractor")
    api_key = st.text_input("Gemini API Key", type="password")

uploaded_file = st.file_uploader("Upload Contract", type=["pdf"])

if not api_key:
    st.info("Enter API Key to start.")
    st.stop()

if uploaded_file:
    if st.button("Extract Clauses", type="primary"):
        with st.spinner("Processing..."):
            # Step 1: Extract and Chunk
            raw_text = extract_text_from_pdf(uploaded_file)
            chunks = chunk_text(clean_text(raw_text))
            
            # DEBUG: Check if text was actually read
            if not chunks:
                st.error("The PDF reader couldn't find any text. Is this a scanned image PDF?")
                st.stop()
            
            st.write(f"🔍 Found {len(chunks)} sections. Sending to AI...")
            
            # Step 2: AI Analysis
            progress_bar = st.progress(0)
            def update_p(done, total):
                progress_bar.progress(done/total)
            
            results = extract_clauses(chunks, api_key, update_p)
            st.session_state.clauses = results
            progress_bar.empty()

    if st.session_state.get("clauses"):
        clauses = st.session_state.clauses
        
        # Filter for only true legal clauses for the final display
        filtered = [c for c in clauses if c.get("is_legal_clause") is True]
        
        # If the AI marked EVERYTHING as false, let's just show everything anyway 
        # so the user doesn't see an empty screen.
        if not filtered:
            filtered = clauses

        st.success(f"Analyzed {len(clauses)} items. Showing {len(filtered)} clauses.")
        
        # Executive Summary
        with st.expander("Summary"):
            st.write(summarize_contract(filtered, api_key))

        # Display results
        for c in filtered:
            st.subheader(f"{c['clause_type']} ({c['risk_level']} Risk)")
            st.write(c['summary'])
            with st.expander("Source Text"):
                st.caption(c.get("original_text", "No text found"))
