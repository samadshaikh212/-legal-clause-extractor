import json
import time
import google.generativeai as genai

SYSTEM_PROMPT = """You are a legal document analyst. Analyze the contract paragraph and extract structured information.
Respond ONLY with a valid JSON object.

Fields to extract:
1. clause_type: One of ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: A plain-English one-sentence summary (max 20 words).
3. risk_level: One of ["High", "Medium", "Low", "None"]
4. risk_reason: Brief reason for the risk level. Empty string if None.
5. key_parties: List of parties mentioned (e.g. ["Client", "Vendor"]).
6. is_legal_clause: true if this is an actual legal provision, false if it's just a header or boilerplate."""

def configure_gemini(api_key: str):
    """Initializes the Gemini API."""
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    """Sends a single paragraph to Gemini and parses the response."""
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph to analyze:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        
        # In JSON mode, response.text should be a clean JSON string
        text = response.text.strip()
        
        # Fail-safe: Manual cleaning in case markdown backticks slip through
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.split("```")[0]
            
        data = json.loads(text.strip())
        
        # Crucial: Store the original text so app.py can display it
        data["original_text"] = chunk
        return data
    except Exception as e:
        print(f"Error analyzing chunk: {e}")
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    """Processes all chunks with a rate-limit delay and JSON mode."""
    configure_gemini(api_key)
    
    # Enable JSON Mode via generation_config
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        
        # We append the result if parsing was successful. 
        # Note: We keep even those marked 'is_legal_clause: false' 
        # so you can debug what the AI is seeing.
        if result:
            results.append(result)
        
        # Respect Free Tier Rate Limits (15 Requests Per Minute)
        time.sleep(2) 
        
        if progress_callback:
            progress_callback(i + 1, total)

    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    """Generates a final executive summary based on the extracted data."""
    if not clauses:
        return "No clauses were detected to summarize."

    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Filter to only 'true' legal clauses for the summary to keep it clean
    legal_clauses = [c for c in clauses if c.get("is_legal_clause") is True]
    if not legal_clauses:
        legal_clauses = clauses[:10] # Fallback to first 10 if none marked True

    summary_input = "\n".join(
        f"- [{c.get('clause_type')}] {c.get('summary')}" for c in legal_clauses
    )

    prompt = f"""You are a legal analyst. Summarize this contract into a 5-sentence executive summary.
    Focus on key obligations and high-risk areas.
    
    Data:
    {summary_input}"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "The AI was unable to generate a summary."
