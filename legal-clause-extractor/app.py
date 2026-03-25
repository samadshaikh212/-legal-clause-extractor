import streamlit as st
from utils import extract_text_from_pdf, clean_text, chunk_text
from extractor import extract_clauses, summarize_contract

st.set_page_config(page_title="Legal Extractor Debug", layout="wide")

with st.sidebar:
    st.title("⚖️ Settings")
    api_key = st.text_input("Gemini API Key", type="password")

st.header("Contract Analysis")
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file and api_key:
    if st.button("Start Analysis"):
        # 1. Read PDF
        raw_text = extract_text_from_pdf(uploaded_file)
        chunks = chunk_text(clean_text(raw_text))
        
        if not chunks:
            st.error("No text found in PDF. Is it a scan?")
            st.stop()
            
        st.info(f"Step 1 Complete: Found {len(chunks)} paragraphs. Starting AI...")

        # 2. AI Processing
        prog = st.progress(0)
        def update_p(d, t):
            prog.progress(d/t, text=f"Processing {d}/{t}...")

        results = extract_clauses(chunks, api_key, update_p)
        st.session_state.clauses = results
        prog.empty()
        
        # 3. Final Check
        if not results:
            st.error("AI returned zero results. Check your API Key or Terminal Logs.")
        else:
            st.success(f"Success! Found {len(results)} items.")
            st.rerun() # Refresh to show cards

if st.session_state.get("clauses"):
    # Display the results
    for i, c in enumerate(st.session_state.clauses):
        with st.container():
            st.markdown(f"### {i+1}. {c.get('clause_type', 'Unknown')}")
            st.write(f"**Summary:** {c.get('summary')}")
            st.info(f"**Risk:** {c.get('risk_level')} - {c.get('risk_reason')}")
            with st.expander("Original Text"):
                st.write(c.get("original_text"))
            st.divider()
