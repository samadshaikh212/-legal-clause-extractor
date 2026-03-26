import json
import re
import time
from groq import Groq


# ── Prompt ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior legal document analyst with 20 years of experience.

Your job is to read a single paragraph from a contract and return a structured JSON analysis.

RULES:
- Respond ONLY with a raw JSON object. No markdown, no backticks, no explanation.
- If the paragraph is NOT a legal clause (e.g. it is a page number, title, table of contents, signature line, or blank filler text), set "is_legal_clause" to false and still return valid JSON.
- Be conservative with risk: only mark "High" if there is a genuine legal risk (unlimited liability, no termination right, waiver of rights, etc.)

REQUIRED JSON FIELDS:
{
  "is_legal_clause": true or false,
  "clause_type": one of ["Obligation", "Right", "Deadline", "Payment", "Termination", "Confidentiality", "Liability", "Indemnity", "Governing Law", "Dispute Resolution", "Warranty", "Intellectual Property", "Other"],
  "summary": "One plain-English sentence, max 25 words.",
  "risk_level": one of ["High", "Medium", "Low", "None"],
  "risk_reason": "One short phrase explaining the risk. Empty string if None.",
  "key_parties": ["Party1", "Party2"],
  "obligations": ["short obligation 1", "short obligation 2"],
  "rights": ["short right 1"]
}

EXAMPLE OUTPUT:
{
  "is_legal_clause": true,
  "clause_type": "Liability",
  "summary": "Neither party is liable for indirect or consequential damages under any circumstances.",
  "risk_level": "High",
  "risk_reason": "Broad exclusion may prevent damage recovery in serious breaches.",
  "key_parties": ["Client", "Vendor"],
  "obligations": [],
  "rights": ["Neither party may claim consequential damages"]
}"""


# ── Core helpers ──────────────────────────────────────────────────────────────

def _clean_json_response(raw: str) -> str:
    """Strip markdown fences and whitespace from model output."""
    raw = raw.strip()
    raw = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    # Extract first JSON object if model adds trailing text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return match.group(0) if match else raw


def _make_client(api_key: str) -> Groq:
    return Groq(api_key=api_key)


# ── Single chunk analysis ─────────────────────────────────────────────────────

def analyze_chunk(chunk: str, client: Groq, retries: int = 2) -> dict | None:
    """
    Send one paragraph to Groq Llama3-70B and return structured result.
    Retries up to `retries` times on failure.
    Returns None if the paragraph is not a legal clause or if all retries fail.
    """
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this contract paragraph:\n\"\"\"\n{chunk.strip()}\n\"\"\""
                    }
                ],
                temperature=0.05,   # very low = more consistent JSON output
                max_tokens=400,
                stop=None,
            )

            raw = response.choices[0].message.content
            cleaned = _clean_json_response(raw)
            result = json.loads(cleaned)

            # Skip non-legal paragraphs silently
            if not result.get("is_legal_clause", False):
                return None

            # Attach original text for display in UI
            result["original_text"] = chunk.strip()

            # Ensure all expected fields exist with safe defaults
            result.setdefault("clause_type", "Other")
            result.setdefault("summary", "")
            result.setdefault("risk_level", "None")
            result.setdefault("risk_reason", "")
            result.setdefault("key_parties", [])
            result.setdefault("obligations", [])
            result.setdefault("rights", [])

            return result

        except json.JSONDecodeError:
            # Model returned non-JSON — retry
            if attempt < retries:
                time.sleep(0.5)
            continue

        except Exception as e:
            error_msg = str(e).lower()
            # Rate limit: wait and retry
            if "rate" in error_msg or "429" in error_msg:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue
            # Any other error: skip this chunk
            return None

    return None


# ── Batch extraction ──────────────────────────────────────────────────────────

def extract_clauses(
    chunks: list[str],
    api_key: str,
    progress_callback=None
) -> list[dict]:
    """
    Analyze all chunks from a contract.

    Args:
        chunks:            List of paragraph strings from utils.chunk_text()
        api_key:           Groq API key
        progress_callback: Optional fn(done: int, total: int) for progress bar

    Returns:
        List of clause dicts, one per detected legal clause.
    """
    client = _make_client(api_key)
    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        # Skip very short chunks — not enough text to be a clause
        if len(chunk.strip()) < 60:
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        result = analyze_chunk(chunk, client)
        if result:
            results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)

        # Small delay between calls to stay within free tier rate limits
        time.sleep(0.2)

    return results


# ── Executive summary ─────────────────────────────────────────────────────────

def summarize_contract(clauses: list[dict], api_key: str) -> str:
    """
    Generate a plain-English executive summary from all extracted clauses.
    Uses a single Groq call over the clause list (not the raw PDF text).
    """
    if not clauses:
        return "No legal clauses were detected in this document."

    client = _make_client(api_key)

    # Build a compact clause list for the prompt
    lines = []
    for c in clauses:
        risk = c.get("risk_level", "None")
        ctype = c.get("clause_type", "Other")
        summary = c.get("summary", "")
        lines.append(f"- [{ctype}] [{risk} risk] {summary}")

    clause_block = "\n".join(lines)

    prompt = f"""You are a legal analyst summarizing a contract for a busy executive who is not a lawyer.

Below are the key clauses extracted from the contract:

{clause_block}

Write a clear executive summary of 5-7 sentences covering:
1. What this contract is about
2. The most important obligations on each party
3. Key deadlines or payment terms if present
4. The biggest legal risks
5. Any unusual or one-sided clauses worth flagging

Write in plain English. No bullet points. No legal jargon."""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return "Executive summary could not be generated. Please review the clauses individually."
