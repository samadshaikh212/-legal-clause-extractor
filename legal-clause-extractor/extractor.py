import json
import time
import google.generativeai as genai

# We simplify the prompt to be less restrictive
SYSTEM_PROMPT = """Analyze this contract text. 
Return ONLY a JSON object with these keys: 
"clause_type", "summary", "risk_level", "risk_reason", "key_parties", "is_legal_clause".
For "is_legal_clause", use true if it's a rule/obligation, false if it's just a title."""

def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)

def analyze_chunk(chunk: str, model) -> dict | None:
    prompt = f"{SYSTEM_PROMPT}\n\nText:\n{chunk}"
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Manually clean backticks if JSON mode fails to strip them
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        data = json.loads(text.strip())
        data["original_text"] = chunk 
        return data
    except Exception as e:
        # This will show up in your Streamlit logs
        print(f"AI Error: {e}")
        return None

def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    configure_gemini(api_key)
    # Force JSON output
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"}
    )

    results = []
    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        if result:
            # IMPORTANT: We removed the 'if is_legal_clause' filter.
            # We want to see EVERYTHING the AI returns to debug.
            results.append(result)
        
        # 2-second sleep to prevent "429 Too Many Requests" on free keys
        time.sleep(2) 
        
        if progress_callback:
            progress_callback(i + 1, len(chunks))
            
    return results

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    if not clauses: return "No data."
    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    summary_input = "\n".join([f"- {c.get('summary')}" for c in clauses[:10]])
    try:
        response = model.generate_content(f"Summarize this in 3 sentences:\n{summary_input}")
        return response.text
    except:
        return "Summary unavailable."
