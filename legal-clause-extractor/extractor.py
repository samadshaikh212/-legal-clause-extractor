import json
import re
import time
import streamlit as st
from groq import Groq


SYSTEM_PROMPT = """You are a senior legal document analyst.

Read the contract paragraph below and return ONLY a JSON object with these exact fields:

{
  "is_legal_clause": true,
  "clause_type": "Obligation",
  "summary": "One plain English sentence under 25 words.",
  "risk_level": "High",
  "risk_reason": "Short reason under 15 words.",
  "key_parties": ["Client", "Vendor"],
  "obligations": ["obligation 1"],
  "rights": ["right 1"]
}

Rules:
- clause_type must be one of: Obligation, Right, Deadline, Payment, Termination, Confidentiality, Liability, Indemnity, Governing Law, Dispute Resolution, Warranty, Intellectual Property, Other
- risk_level must be one of: High, Medium, Low, None
- Set is_legal_clause to false only for page numbers, headers, signature lines, or table of contents
- Return ONLY the JSON object. No explanation. No markdown. No backticks."""

MODEL = "llama-3.3-70b-versatile"


def analyze_chunk(chunk: str, client: Groq) -> dict | None:
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this paragraph:\n\n{chunk.strip()}"}
                ],
                temperature=0.0,
                max_tokens=350,
            )

            raw = response.choices[0].message.content.strip()
            raw = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
            raw = re.sub(r'^```\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)

            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not match:
                continue
            raw = match.group(0)

            result = json.loads(raw)

            if not result.get("is_legal_clause", True):
                return None

            result["original_text"] = chunk.strip()
            result.setdefault("clause_type", "Other")
            result.setdefault("summary", chunk[:100])
            result.setdefault("risk_level", "None")
            result.setdefault("risk_reason", "")
            result.setdefault("key_parties", [])
            result.setdefault("obligations", [])
            result.setdefault("rights", [])
            return result

        except json.JSONDecodeError:
            time.sleep(0.5)
            continue

        except Exception as e:
            msg = str(e).lower()
            if "rate" in msg or "429" in msg:
                time.sleep(5 * (attempt + 1))
                continue
            st.error(f"Groq API error on chunk: {str(e)}")
            return None

    return None


def extract_clauses(chunks: list, api_key: str, progress_callback=None) -> list:
    try:
        client = Groq(api_key=api_key)
        client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=5,
        )
    except Exception as e:
        st.error(f"Cannot connect to Groq API: {str(e)}")
        return []

    results = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) < 40:
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        result = analyze_chunk(chunk, client)
        if result:
            results.append(result)

        if progress_callback:
            progress_callback(i + 1, total)

        time.sleep(0.15)

    return results


def summarize_contract(clauses: list, api_key: str) -> str:
    if not clauses:
        return "No clauses were extracted."

    try:
        client = Groq(api_key=api_key)
        lines = [
            f"- [{c.get('clause_type','Other')}] [{c.get('risk_level','None')} risk] {c.get('summary','')}"
            for c in clauses
        ]

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": (
                    "You are a legal analyst. Write a plain-English executive summary "
                    "(5-6 sentences) of this contract for a non-lawyer. Cover: what it's about, "
                    "key obligations, deadlines, payment terms, and biggest risks.\n\n"
                    "Clauses:\n" + "\n".join(lines)
                )
            }],
            temperature=0.3,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Summary generation failed: {str(e)}"
