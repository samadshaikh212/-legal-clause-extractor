import json
import google.generativeai as genai

SYSTEM_PROMPT = """You are a legal document analyst. Analyze the contract paragraph and extract structured information.
Respond ONLY with a valid JSON object.

Fields:
1. clause_type: ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: One-sentence summary (max 20 words).
3. risk_level: ["High", "Medium", "Low", "None"]
4. risk_reason: Brief reason.
5. key_parties: List of parties.
6. is_legal_clause: true if this is a legal provision, false if it is just a title/header."""

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        data = json.loads(response.text.strip())
        
        # Add the original text for the UI
        data["original_text"] = chunk 
        
        # DEBUG: If you are running locally, this will show you what the AI is thinking
        # print(f"AI classified as legal: {data.get('is_legal_clause')}")
        
        return data
    except Exception as e:
        print(f"JSON Error: {e}")
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    configure_gemini(api_key)
    # Using JSON mode to prevent formatting errors
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        if result:
            # CHANGE: We now keep the result REGARDLESS of the is_legal_clause flag 
            # to ensure the list isn't empty.
            results.append(result)
        
        if progress_callback:
            progress_callback(i + 1, len(chunks))
    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    if not clauses: return "No data."
    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    summary_input = "\n".join([f"- {c.get('summary')}" for c in clauses[:15]])
    prompt = f"Summarize these contract points in 5 sentences:\n{summary_input}"
    try:
        return model.generate_content(prompt).text
    except:
        return "Summary unavailable."
