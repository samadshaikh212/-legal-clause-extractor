import json
import google.generativeai as genai

SYSTEM_PROMPT = """You are a legal document analyst. Analyze the contract paragraph and extract structured information.
Respond ONLY with a valid JSON object.

Fields to extract:
1. clause_type: ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: Plain-English one-sentence summary (max 20 words).
3. risk_level: ["High", "Medium", "Low", "None"]
4. risk_reason: Brief reason for risk. Empty if None.
5. key_parties: List of parties mentioned.
6. is_legal_clause: true if this is a legal provision, false if it is a header, title, or signature block."""

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        # With JSON mode, we can parse the response directly
        data = json.loads(response.text.strip())
        
        # We attach the original text so app.py can display it in the expander
        data["original_text"] = chunk 
        return data
    except Exception:
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    configure_gemini(api_key)
    
    # CRITICAL: Added generation_config for strict JSON mode
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        # If parsing succeeded, we keep the clause
        if result:
            # We check the AI's classification, but you can remove this 'if' 
            # to see EVERY paragraph the AI processes
            if result.get("is_legal_clause") is True:
                results.append(result)
        
        if progress_callback:
            progress_callback(i + 1, len(chunks))
    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    if not clauses: return "No clauses found."
    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    summary_input = "\n".join([f"- {c.get('summary')}" for c in clauses[:20]])
    prompt = f"Provide a 5-sentence executive summary of this contract based on these points:\n{summary_input}"
    try:
        return model.generate_content(prompt).text
    except:
        return "Summary unavailable."
