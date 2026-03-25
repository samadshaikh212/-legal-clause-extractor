import json
import google.generativeai as genai

SYSTEM_PROMPT = """You are a legal document analyst. Analyze the given contract paragraph and extract structured information.
Respond ONLY with a valid JSON object.

For each paragraph, identify:
1. clause_type: one of ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: a plain-English one-sentence summary (max 20 words)
3. risk_level: one of ["High", "Medium", "Low", "None"]
4. risk_reason: brief reason for the risk level (max 15 words).
5. key_parties: list of parties mentioned (e.g. ["Client", "Vendor"])
6. is_legal_clause: true if this is an actual legal clause, false if it's boilerplate/header/page number"""

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph to analyze:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        data = json.loads(text.strip())
        # We attach the original text here so app.py can display it later
        data["original_text"] = chunk 
        return data
    except Exception:
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    configure_gemini(api_key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        # Check if it's a valid legal clause before adding
        if result and result.get("is_legal_clause") is True:
            results.append(result)
        
        if progress_callback:
            progress_callback(i + 1, total)

    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    if not clauses: return "No clauses found."
    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    summary_text = "\n".join([f"- {c['summary']}" for c in clauses[:15]]) # Limit to top 15 for context window
    prompt = f"Summarize the following contract points into a 5-sentence executive summary:\n{summary_text}"
    
    try:
        return model.generate_content(prompt).text
    except:
        return "Summary unavailable."
