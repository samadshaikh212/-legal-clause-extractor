import fitz  # PyMuPDF
import re


# ── PDF Reading ───────────────────────────────────────────────────────────────

def extract_text_from_pdf(uploaded_file) -> str:
    """Read PDF bytes and return full plain text."""
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text("text")
    doc.close()
    return full_text


# ── Text Cleaning ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalize whitespace while keeping legal symbols and clause numbers."""
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'(?m)^\s*[-–]?\s*\d{1,3}\s*[-–]?\s*$', '', text)
    text = re.sub(r'(?m)^\s*[_\-]{4,}\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Text Chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, min_len: int = 30, max_len: int = 1500) -> list[str]:
    """
    Split contract text into clause-level chunks.
    Detects numbered clause boundaries like 1.1, 2.3, 7.2 etc.
    Falls back to sentence splitting for oversized chunks.
    """
    chunks = []
    lines = text.split('\n')
    current_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Blank line — flush if buffer is large enough
            if current_lines:
                current_text = ' '.join(current_lines).strip()
                if len(current_text) > max_len:
                    chunks.append(current_text)
                    current_lines = []
            continue

        # Detect numbered clause start: "1.1 The Vendor..." or "2. PAYMENT TERMS"
        is_new_clause = bool(re.match(r'^\d+\.\d*\s', stripped)) or \
                        bool(re.match(r'^\d+\.\s+[A-Z]', stripped))

        if is_new_clause and current_lines:
            current_text = ' '.join(current_lines).strip()
            if len(current_text) >= min_len:
                chunks.append(current_text)
            current_lines = [stripped]
        else:
            current_lines.append(stripped)

    # Flush remaining lines
    if current_lines:
        current_text = ' '.join(current_lines).strip()
        if len(current_text) >= min_len:
            chunks.append(current_text)

    # Split any chunks that are still too large
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            final_chunks.append(chunk)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            current = ""
            for sentence in sentences:
                if len(current) + len(sentence) + 1 > max_len and current:
                    final_chunks.append(current.strip())
                    current = sentence
                else:
                    current = (current + " " + sentence).strip()
            if current:
                final_chunks.append(current)

    return final_chunks


# ── PDF Stats ─────────────────────────────────────────────────────────────────

def get_pdf_stats(text: str) -> dict:
    """Return basic stats about the extracted text."""
    words = len(text.split())
    paragraphs = len([p for p in text.split('\n\n') if p.strip()])
    pages_est = max(1, round(words / 350))
    return {
        "words": words,
        "paragraphs": paragraphs,
        "pages_est": pages_est,
    }
