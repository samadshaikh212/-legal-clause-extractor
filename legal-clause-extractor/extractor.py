import json
import re
import google.generativeai as genai


SYSTEM_PROMPT = """You are a legal document analyst. Analyze the given contract paragraph and extract structured information.

For each paragraph, identify:
1. clause_type: one of ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Other"]
2. summary: a plain-English one-sentence summary (max 20 words)
3. risk_level: one of ["High", "Medium", "Low", "None"]
4. risk_reason: brief reason for the risk level (max 15 words). Empty string if risk is None.
5. key_parties: list of parties mentioned (e.g. ["Client", "Vendor"])
6. is_legal_clause: true if this is an actual legal clause, false if it's boilerplate/header/page number

Respond ONLY with a valid JSON object. No explanation, no markdown, no backticks. Example:
{
  "clause_type": "Obligation",
  "summary": "Vendor must deliver software within 30 days of signing.",
  "risk_level": "Medium",
  "risk_reason": "Tight deadline with no extension clause.",
  "key_parties": ["Vendor", "Client"],
  "is_legal_clause": true
}"""


def configure_gemini(api_key: str):
    genai.configure(api_key=api_key)


def analyze_chunk(chunk: str, model) -> dict | None:
    """Send one paragraph to Gemini and parse the JSON response."""
    prompt = f"{SYSTEM_PROMPT}\n\nParagraph to analyze:\n\"\"\"\n{chunk}\n\"\"\""

    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if model adds them
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        result = json.loads(raw)

        # Only return if it's actually a legal clause
        if not result.get("is_legal_clause", False):
            return None

        result["original_text"] = chunk
        return result

    except (json.JSONDecodeError, Exception):
        return None


def extract_clauses(chunks: list[str], api_key: str, progress_callback=None) -> list[dict]:
    """
    Run analysis on all chunks.
    progress_callback(i, total) called after each chunk if provided.
    """
    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        result = analyze_chunk(chunk, model)
        if result:
            results.append(result)
        if progress_callback:
            progress_callback(i + 1, total)

    return results


def summarize_contract(clauses: list[dict], api_key: str) -> str:
    """Generate a plain-English executive summary of the whole contract."""
    if not clauses:
        return "No clauses extracted."

    configure_gemini(api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    clause_summaries = "\n".join(
        f"- [{c['clause_type']}] {c['summary']}" for c in clauses
    )

    prompt = f"""You are a legal analyst. Based on these extracted clauses from a contract, write a concise executive summary (4-6 sentences) in plain English for a non-lawyer. Highlight the most important obligations, rights, and risks.

Clauses:
{clause_summaries}

Executive Summary:"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "Could not generate summary."
