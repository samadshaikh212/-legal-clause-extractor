import json
import google.generativeai as genai

SYSTEM_PROMPT = """You are a legal document analyst. Analyze the given contract paragraph and extract structured information.

For each paragraph, identify:
1. clause_type: one of ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: a plain-English one-sentence summary (max 20 words)
3. risk_level: one of ["High", "Medium", "Low", "None"]
4. risk_reason: brief reason for the risk level (max 15 words). Empty string if risk is None.
5. key_parties: list of parties mentioned (e.g. ["Client", "Vendor"])
6. is_legal_clause: true if this is an actual legal clause, false if it's boilerplate/header/page number

Respond ONLY with a valid JSON object."""

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    """Send one paragraph to Gemini and parse the JSON response."""
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph to analyze:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Robust JSON cleaning: handle potential markdown backticks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"Error parsing chunk: {e}")
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    """Run analysis on all chunks with JSON mode enabled."""
    configure_gemini(api_key)
    
    # We use generation_config to force the model to output valid JSON
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        
        # We only keep the result if it was successfully parsed 
        # AND the AI confirmed it is a legal clause (not a header)
        if result and result.get("is_legal_clause") is True:
            results.append(result)
            
        if progress_callback:
            progress_callback(i + 1, total)

    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    """Generate a plain-English executive summary."""
    if not clauses:
        return "No clauses extracted to summarize."

    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    clause_summaries = "\n".join(
        f"- [{c.get('clause_type', 'Other')}] {c.get('summary', 'No summary available')}" 
        for c in clauses
    )

    prompt = f"""You are a legal analyst. Based on these extracted clauses, write a concise executive summary (4-6 sentences) for a non-lawyer.
    
    Clauses:
    {clause_summaries}
    
    Executive Summary:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Could not generate summary."
